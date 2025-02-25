import cv2
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QLabel, QDialogButtonBox
)


class DeviceConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Connection")
        self.setGeometry(200, 200, 400, 400)

        # Layout
        layout = QVBoxLayout()

        # List available cameras for main video
        self.main_camera_list = QListWidget()
        self.main_camera_list.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(QLabel("Select Camera for Main Video:"))
        layout.addWidget(self.main_camera_list)

        # List available cameras for secondary video
        self.secondary_camera_list = QListWidget()
        self.secondary_camera_list.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(QLabel("Select Camera for Secondary Video:"))
        layout.addWidget(self.secondary_camera_list)

        # Populate camera lists
        self.detect_cameras()

        # List available serial ports
        self.serial_list = QListWidget()
        self.serial_list.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(QLabel("Available Serial Ports:"))
        layout.addWidget(self.serial_list)

        # Populate serial ports
        self.detect_serial_ports()

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def detect_cameras(self):
        # Detect available cameras and populate both lists
        for i in range(5):  # Check up to 5 devices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.main_camera_list.addItem(f"Camera {i}")
                self.secondary_camera_list.addItem(f"Camera {i}")
                cap.release()

    def detect_serial_ports(self):
        # List all available serial ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.serial_list.addItem(f"{port.device} - {port.description}")
