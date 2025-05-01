import os

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout, QCompleter
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QStringListModel
from PyQt5.QtGui import QFont
import random
import smtplib
from email.mime.text import MIMEText
import logging
from datetime import datetime


class EmailLoginDialog(QDialog):
    login_success = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("登录")
        self.setFixedSize(400, 300)
        self.verification_code = None
        self.target_email = None
        self.countdown = 60
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

        self.setStyleSheet("""
            QLabel {
                font-size: 11.5pt;
                color: #333;
                    }
            QLineEdit {
                padding: 6px;
                font-size: 11pt;
                border: 1px solid #aaa;
                border-radius: 6px;
                    }
            QPushButton {
                height: 36px;
                background-color: #D6C8D3;
                color: black;
                font-weight: bold;
                font-size: 10.5pt;
                border: none;
                border-radius: 6px;
                min-width: 100px;
                    }
            QPushButton:disabled {
                background-color: #bbbbbb;
                color: #eee;
                    }
            QPushButton:hover:!disabled {
                background-color: #EEDA92;
                    }
                """)

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        self.info_label = QLabel("请输入您的邮箱登录\n我们会为您发送代码运行通知")
        self.info_label.setFont(QFont("微软雅黑", 12))
        self.info_label.setAlignment(Qt.AlignCenter)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your_email@email.com")
        self.email_input.setClearButtonEnabled(True)
        self.domains = ["qq.com", "163.com", "126.com", "gmail.com", "outlook.com", "hotmail.com"]
        # 补全效果
        self.completer_model = QStringListModel()
        self.email_completer = QCompleter(self.completer_model, self)
        self.email_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.email_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.email_completer.activated.connect(self.insert_completion)
        self.email_completer.popup().setStyleSheet("""
            QListView {
                background-color: #f9f9f9;
                color: #404346;
                font-size: 10.5pt;
                padding: 4px;
                border: 1px solid #aaa;
                selection-background-color: #F4E0E1;
                selection-color: #504D77;
            }
        """)

        # 文本变化时我们手动调用弹出逻辑
        self.email_input.textEdited.connect(self.update_domain_completer)

        self.send_code_button = QPushButton("发送验证码")
        self.send_code_button.clicked.connect(self.send_verification_code)

        email_row = QHBoxLayout()
        email_row.addWidget(self.email_input)
        email_row.addWidget(self.send_code_button)

        self.code_tip_label = QLabel()
        self.code_tip_label.setAlignment(Qt.AlignCenter)
        self.code_tip_label.setStyleSheet("color: #666;")
        self.code_tip_label.setVisible(False)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("请输入验证码")
        self.code_input.setMaxLength(6)
        self.code_input.setClearButtonEnabled(True)
        self.code_input.setVisible(False)

        self.verify_button = QPushButton("验证并进入")
        self.verify_button.setVisible(False)
        self.verify_button.clicked.connect(self.verify_code)

        layout.addWidget(self.info_label)
        layout.addLayout(email_row)
        layout.addWidget(self.code_tip_label)
        layout.addWidget(self.code_input)
        layout.addWidget(self.verify_button)
        layout.addStretch()

        self.setLayout(layout)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def update_domain_completer(self, text: str):
        if "@" not in text:
            return

        local, domain_part = text.split("@", 1)
        self.current_local_part = local.strip()

        # 忽略拼音输入法状态干扰，强制更新内容
        filtered_domains = []
        domain_part_lower = domain_part.lower()
        if domain_part_lower == "":
            filtered_domains = self.domains
        else:
            for domain in self.domains:
                if domain.startswith(domain_part_lower):
                    filtered_domains.append(domain)

        if not filtered_domains:
            return

        # 显示完整格式，如 user@domain
        suggestions = [f"{local}@{d}" for d in filtered_domains]

        self.completer_model.setStringList(suggestions)
        self.email_completer.setModel(self.completer_model)

        self.email_completer.setWidget(self.email_input)
        self.email_completer.complete()

    def insert_completion(self, full_email: str):
        self.email_input.setText(full_email)

    def send_verification_code(self):
        email = self.email_input.text().strip()
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "格式错误", "请输入合法的邮箱地址")
            return

        self.verification_code = f"{random.randint(100000, 999999)}"
        self.target_email = email

        try:
            self.send_email(self.target_email, self.verification_code)
            self.code_tip_label.setText("验证码已发送")
            self.code_tip_label.setFont(QFont("微软雅黑", 12))
            self.code_tip_label.setVisible(True)
            self.code_input.setVisible(True)
            self.verify_button.setVisible(True)

            self.send_code_button.setDisabled(True)
            self.countdown = 60
            self.send_code_button.setText("重新发送 (60)")
            self.timer.start(1000)

            QMessageBox.information(self, "发送成功", f"验证码已发送！请查收邮箱。")
        except Exception as e:
            QMessageBox.critical(self, "发送失败", f"邮件发送失败：\n{str(e)}")

    def verify_code(self):
        entered = self.code_input.text().strip()
        if entered == self.verification_code:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            ts_str = now.strftime("%Y%m%d%H%M%S")
            log_dir = os.path.join("logs", date_str, ts_str)
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "session.log")
            logging.basicConfig(
                    filename = log_path,
                    level = logging.INFO,
                    format = "%(asctime)s %(levelname)s: %(message)s",
                    datefmt = "%Y-%m-%d %H:%M:%S"
                            )
            logging.info(f"用户登录邮箱：{self.target_email}")
            self.login_success.emit(self.target_email)
            self.accept()
        else:
            QMessageBox.warning(self, "验证码错误", "请输入正确的验证码。")

    def update_timer(self):
        self.countdown -= 1
        if self.countdown > 0:
            self.send_code_button.setText(f"重新发送({self.countdown})")
        else:
            self.timer.stop()
            self.send_code_button.setEnabled(True)
            self.send_code_button.setText("发送验证码")

    def send_email(self, to_email, code):
        smtp_server = "smtp.163.com"
        smtp_port = 465
        sender_email = "18656987650@163.com"
        sender_password = "AHhDF3AwsyEUk8LM"

        subject = "PyMonitor 验证码"
        body = f"Dear:\n     您的验证码是：{code}(有效期3分钟),我们悄咪咪的,不要告诉别人哦~"

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = to_email

        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
