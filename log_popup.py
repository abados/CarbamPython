from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
from PyQt5.QtCore import Qt


class LogPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Window")
        self.setGeometry(200, 200, 600, 400)

        # Layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Log area
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.log_window.setStyleSheet("background-color: lightgray; font-size: 12px;")
        self.layout.addWidget(self.log_window)

        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        self.layout.addWidget(self.close_button)

    def log_message(self, message):
        self.log_window.append(message)
        self.log_window.ensureCursorVisible()
