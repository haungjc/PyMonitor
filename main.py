import locale
import smtplib
import sys
import os
import json
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from PyQt5.QtWidgets import QToolButton, QMenu, QAction, QHBoxLayout, QDialog
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QDialog
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QMessageBox, QComboBox, QLabel, QTextEdit
)
from PyQt5.QtCore import QThread, pyqtSignal, QPoint, Qt
from PyQt5.QtGui import QCursor
from menu import AboutDialog
from login import EmailLoginDialog
HISTORY_FILE = "history_paths.json"
SESSION_FILE = "login_session.json"


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"env_paths": [], "script_paths": []}


def save_history(env_paths, script_paths):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "env_paths": env_paths,
            "script_paths": script_paths
        }, f, indent=2, ensure_ascii=False)


# ========== 子线程运行器 ==========
class ProcessRunner(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, python_path, script_path):
        super().__init__()
        self.python_path = python_path
        self.script_path = script_path
        self.output_lines = []

    def run(self):
        try:
            script_dir = os.path.dirname(self.script_path)
            # 在 Windows 上隐藏子进程窗口
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen(
                [self.python_path, self.script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=script_dir,
                bufsize=1,
                universal_newlines=True,
                encoding=locale.getpreferredencoding(False),
                errors='replace',
                startupinfo=startupinfo
            )

            for line in process.stdout:
                text = line.rstrip()
                self.output_lines.append(text)
                self.output_signal.emit(text)

            process.stdout.close()
            return_code = process.wait()
            self.finished_signal.emit(return_code)

        except Exception as e:
            self.output_signal.emit(f"[运行错误] {str(e)}")
            self.finished_signal.emit(-1)


# ========== 主界面 ==========
class MonitorApp(QWidget):
    def __init__(self, email_address=None):
        super().__init__()
        self.setWindowTitle("PyMonitor--当代科研(牛马)利器！")
        self.resize(800, 750)

        self.recipient_email = email_address or "default@example.com"

        self.layout = QVBoxLayout()

        # --- 顶部“☰”菜单按钮 ---
        self.menu_button = QToolButton(self)
        self.menu_button.setFixedSize(24, 24)
        self.menu_button.setText("☰")
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        self.menu_button.setStyleSheet("font-size:8pt; padding:8px;")  # 可调样式

        # 构造菜单并绑定退出登录
        self.top_menu = QMenu(self)

        about_action = QAction("关于 PyMonitor", self)
        about_action.triggered.connect(self.show_about)
        self.top_menu.addAction(about_action)

        open_logs_action = QAction("日志", self)
        open_logs_action.triggered.connect(self.open_log_folder)
        self.top_menu.addAction(open_logs_action)

        logout_act = QAction("退出登录", self)
        logout_act.triggered.connect(self.logout)
        self.top_menu.addAction(logout_act)
        self.menu_button.setMenu(self.top_menu)

        # 把按钮放到 layout 最前面
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)  # 子布局自身不留内边距
        top_bar.setSpacing(0)  # 子布局内部也无额外间距
        top_bar.addStretch()
        top_bar.addWidget(self.menu_button)
        self.layout.insertLayout(0, top_bar)
# --------------布局------------------------------
        self.env_combo = QComboBox()
        self.env_combo.setEditable(True)
        self.env_combo.setPlaceholderText("请选择 Conda 环境路径")

        self.script_combo = QComboBox()
        self.script_combo.setEditable(True)
        self.script_combo.setPlaceholderText("请选择你要运行的代码文件")

        self.choose_env_button = QPushButton("选择 Conda Env 根目录")
        self.choose_script_button = QPushButton("选择 Python 可执行文件")
        self.run_button = QPushButton("Running")

        self.output_console = QTextEdit()
        self.output_console.setReadOnly(True)
        self.output_console.setStyleSheet("background-color: black; color: lightgreen; font-family: Consolas;")

        # 布局组件添加
        self.layout.addWidget(QLabel("Conda 环境路径:"))
        self.layout.addWidget(self.env_combo)
        self.layout.addWidget(self.choose_env_button)

        self.layout.addWidget(QLabel("Python 脚本路径:"))
        self.layout.addWidget(self.script_combo)
        self.layout.addWidget(self.choose_script_button)

        self.layout.addWidget(self.run_button)
        self.layout.addWidget(QLabel("monitor:"))
        self.layout.addWidget(self.output_console)

        self.setLayout(self.layout)

        # ==== 托盘图标初始化 ====-------------------------------------
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("image/icon.ico"))
        self.tray_icon.setToolTip("PyMonitor 监控代码运行状态")

        self.tray_menu = QMenu(self)

        about_action = QAction("关于 PyMonitor", self)
        about_action.triggered.connect(self.show_about)
        self.tray_menu.addAction(about_action)

        open_logs_action = QAction("日志", self)
        open_logs_action.triggered.connect(self.open_log_folder)
        self.tray_menu.addAction(open_logs_action)

        quit_action = QAction("退出应用", self)
        quit_action.triggered.connect(self.exit_app)
        self.tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)

        self.tray_icon.activated.connect(self.on_tray_icon_activated)  # ← 左键点击绑定
        self.tray_icon.show()

        # 信号绑定
        self.choose_env_button.clicked.connect(self.choose_env)
        self.choose_script_button.clicked.connect(self.choose_script)
        self.run_button.clicked.connect(self.run_and_monitor)

        # 历史加载
        self.history = load_history()
        self.env_combo.addItems(self.history["env_paths"])
        self.script_combo.addItems(self.history["script_paths"])
        default_font = QFont("微软雅黑", 11)
        self.setFont(default_font)

        # 设置整体内边距和控件间距
        self.layout.setSpacing(12)
        self.layout.setContentsMargins(20, 8, 18, 18)

        # 美化按钮
        button_style = """
            QPushButton {
                background-color: #D6C8D3;
                color: black;
                font-weight: bold;
                font-size: 10.5pt;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #EEDA92;
            }
        """
        for btn in [self.choose_env_button, self.choose_script_button, self.run_button]:
            btn.setFixedHeight(36)
            btn.setStyleSheet(button_style)

        # 下拉框样式
        combo_style = """
            QComboBox {
                padding: 4px;
                font-size: 11pt;
            }
        """
        self.env_combo.setFixedHeight(32)
        self.script_combo.setFixedHeight(32)
        self.env_combo.setStyleSheet(combo_style)
        self.script_combo.setStyleSheet(combo_style)

    def logout(self):
        # 删除 session 文件
        try:
            os.remove(SESSION_FILE)
        except FileNotFoundError:
            pass

        # 隐藏主界面和托盘
        self.hide()
        self.tray_icon.hide()

        # 创建并显示登录窗口
        login = EmailLoginDialog()
        login.setWindowModality(Qt.ApplicationModal)
        login.activateWindow()
        login.raise_()

        if login.exec_() == QDialog.Accepted:
            email = login.email_input.text().strip()
            save_session(email)
            self.recipient_email = email

            self.tray_icon.show()  # 恢复托盘
            self.show()  # 恢复主界面
        else:
            QApplication.quit()  # 用户取消登录，退出程序

    def choose_env(self):
        folder = QFileDialog.getExistingDirectory(self, "选择 Conda 环境目录")
        if not folder:
            return
        win_path = os.path.join(folder, "python.exe")
        unix_path = os.path.join(folder, "bin", "python")
        if os.path.isfile(win_path):
            env_path = win_path
        elif os.path.isfile(unix_path):
            env_path = unix_path
        else:
            QMessageBox.warning(self, "错误", "未找到 python 可执行文件")
            return
        self.env_combo.setCurrentText(env_path)
        if env_path not in self.history["env_paths"]:
            self.history["env_paths"].append(env_path)
            self.env_combo.addItem(env_path)
            save_history(self.history["env_paths"], self.history["script_paths"])

    def choose_script(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择 Python 文件", "", "Python 文件 (*.py)")
        if file:
            self.script_combo.setCurrentText(file)
            if file not in self.history["script_paths"]:
                self.history["script_paths"].append(file)
                self.script_combo.addItem(file)
                save_history(self.history["env_paths"], self.history["script_paths"])

    def run_and_monitor(self):
        env_path = self.env_combo.currentText()
        script_path = self.script_combo.currentText()
        logging.info(f"开始运行脚本，Conda 环境：{env_path}，脚本路径：{script_path}")
        if not os.path.isfile(env_path):
            QMessageBox.warning(self, "错误", "无效的 Conda Python 路径")
            return
        if not os.path.isfile(script_path):
            QMessageBox.warning(self, "错误", "无效的 Python 可执行文件路径")
            return

        self.output_console.clear()
        self.output_console.append(f">>> 开始执行：{script_path}\n")

        self.runner = ProcessRunner(env_path, script_path)
        self.runner.output_signal.connect(self.handle_output)
        self.runner.finished_signal.connect(self.handle_finished)
        self.runner.start()

    def exit_app(self):
        # 1. 隐藏托盘图标
        self.tray_icon.hide()

        # 2. 停止可能运行中的线程
        if hasattr(self, 'runner') and self.runner.isRunning():
            self.runner.terminate()
            self.runner.wait()

        # 3. 完全退出应用
        QApplication.instance().quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "程序最小化",
            "程序已最小化到系统托盘，右键托盘图标可操作。",
            QSystemTrayIcon.Information,
            3000
        )

    def open_log_folder(self):
        """
        在文件管理器中打开当天的日志根目录（logs），
        也可调整为打开当前会话目录。
        """
        # 按您之前的目录结构，日志都在 logs/YYYY-MM-DD/HHMMSS/session.log
        base_dir = os.path.join(os.getcwd(), "logs")
        if not os.path.isdir(base_dir):
            QMessageBox.warning(self, "日志文件夹不存在", f"未找到日志目录：{base_dir}")
            return

        # Windows 平台可用 os.startfile，跨平台可用 QDesktopServices
        try:
            os.startfile(base_dir)
        except AttributeError:
            # fallback for non-Windows
            from PyQt5.QtGui import QDesktopServices
            from PyQt5.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(base_dir))

    def show_window(self):
        self.showNormal()
        self.activateWindow()

    def handle_output(self, text: str):
        # 1) 追加到 QTextEdit 控制台
        self.output_console.append(text)
        # 2) 写入日志
        logging.info(text)

    def show_about(self):
        self.about_window = AboutDialog(self)
        self.about_window.show()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # 左键单击打开窗口
            self.show_window()
        elif reason == QSystemTrayIcon.Context:  # 右键打开菜单
            base_pos = QCursor.pos()
            offset = QPoint(+6, -55)  # 向右偏移10像素，向上偏移100像素
            self.tray_menu.exec_(base_pos + offset)

    def send_email(self, to_email: str, subject: str, body: str):
        """
        通用邮件发送函数，使用您在登录界面中配置好的发信账号。
        """
        smtp_server = "smtp.163.com"
        smtp_port = 465
        sender_email = "18656987650@163.com"
        sender_password = "AHhDF3AwsyEUk8LM"  # 请使用安全存储或环境变量

        # 构造邮件
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = to_email

        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()

    def handle_finished(self, exit_code: int):
        """
        进程结束回调：根据 exit_code 发送邮件并记录日志。
        """
        # 先在控制台显示结束信息
        self.output_console.append(f"\n>>> 进程结束，退出码：{exit_code}")

        # 时间戳（北京时间，假设系统时区即北京时间）
        now = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")

        # 拼装邮件主题与正文
        if exit_code == 0:
            subject = "PyMonitor：运行成功通知"
            body = (
                f"恭喜！您的代码于北京时间{now}运行完成没有任何报错\n"
                "请抓紧时间验收成果,期待您的成果。\n祝好！"
            )
        else:
            # 从 runner 收集的输出中提取 traceback
            lines = self.runner.output_lines
            tb_start = 0
            for i, line in enumerate(lines):
                if line.startswith("Traceback (most recent call last):"):
                    tb_start = i
                    break
            traceback_snippet = "\n".join(lines[tb_start:]) if tb_start < len(lines) else "无可用错误信息"
            subject = "PyMonitor：运行失败通知"
            body = (
                "很遗憾，您的代码出现了一些小错误。\n"
                f"错误定位于：\n{traceback_snippet}\n"
                "麻溜的赶紧去改代码，不然晚上要来打你屁屁了！！！"
            )

        # 发送邮件
        try:
            # 假设您已有一个 send_email 方法可用
            self.send_email(self.recipient_email, subject, body)
            logging.info(f"邮件发送成功 to={self.recipient_email} subject={subject}")
        except Exception as e:
            logging.error(f"邮件发送失败 to={self.recipient_email} error={e}")


def load_session():
    """
    若 session.json 存在且未过期，返回 (email:str, True)；
    否则返回 (None, False).
    """
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            last = datetime.fromisoformat(data.get("last_login"))
            if datetime.now() - last < timedelta(hours=12):
                return data.get("email"), True
        except Exception:
            pass
    return None, False


def save_session(email: str):
    """
    将当前时间和邮箱写入 session.json
    """
    data = {
        "email": email,
        "last_login": datetime.now().isoformat()
    }
    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ========== 程序入口 ==========
if __name__ == "__main__":
    app = QApplication(sys.argv)
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(__file__)
    icon_path = os.path.join(base, "image", "icon1.ico")
    app.setWindowIcon(QIcon(icon_path))
    app.setQuitOnLastWindowClosed(False)
    email_address, valid = load_session()
    if not valid:
        # 弹出邮箱登录窗口
        login_dialog = EmailLoginDialog()
        if login_dialog.exec_() == QDialog.Accepted:
            email_address = login_dialog.email_input.text().strip()  # 保存邮箱
            save_session(email_address)
        else:
            sys.exit(0)  # 用户取消登录，退出程序
    window = MonitorApp(email_address=email_address)
    window.tray_icon.setIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec_())

