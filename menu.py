from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
import sys, os

if getattr(sys, 'frozen', False):
    base = sys._MEIPASS
else:
    base = os.path.dirname(__file__)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 PyMonitor")
        self.setFixedSize(500, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 应用介绍文字
        label = QLabel("本软件由 “纯鼠啦” 开发维护\n任何疑问和建议请扫码告知本人")
        label.setFont(QFont("微软雅黑", 12))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # 添加二维码图像
        image_label = QLabel()
        image_path = os.path.join(base, "image", "wx1.png")
        pixmap = QPixmap(image_path).scaled(450, 450, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)

        # 版权信息
        copyright = QLabel("@ 2025 ChunShula 版权所有")
        copyright.setFont(QFont("微软雅黑", 11))
        copyright.setAlignment(Qt.AlignCenter)
        copyright.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addWidget(copyright)

        self.setLayout(layout)
