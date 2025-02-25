
import sys
import cv2
import socket
import os
import logging
import ast
import time  # For latency calculationX
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QSlider,
    QPushButton, QWidget, QGridLayout
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from log_popup import LogPopup  # Import the log pop-up
from config import import_config
from Joystick import RCSimulator
from PyQt5.QtMultimedia import QSound
from VideoCaptureHandler import VideoManager
# Determine the directory of the script or executable
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(script_dir, "remote_driving_log.txt")

# Configure logging
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Load the configuration
config = import_config()

# Access the variables
main_video_port = config["main_video_port"]
secondary_video_port = config["sacandary_video_port"]


steering_factor = 3
from threading import Thread
from PyQt5.QtCore import pyqtSignal, QThread


from threading import Thread
import time


if int(config["connected_to_system"])==1: #1 for True 2 for False
    video_connected=False
else:
    video_connected=True
print(video_connected)


class RemoteDrivingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Remote Driving System")
        self.setGeometry(100, 100, 1500, 900)

        # Main widget and layout
        self.central_widget = QWidget()
        self.main_layout = QGridLayout()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        # Main video label
        self.main_video_label = QLabel("Main Video")
        self.main_video_label.setStyleSheet("background-color: black; color: yellow; font-size: 20px;")
        self.main_video_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.main_video_label, 0, 0, 4, 4)  # Rows 0-3, Cols 0-3

        # Secondary video label
        self.secondary_video_label = QLabel("Secondary Video")
        self.secondary_video_label.setStyleSheet("background-color: gray; color: white; font-size: 16px;")
        self.secondary_video_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.secondary_video_label, 0, 4, 2, 2)  # Rows 0-1, Cols 4-5



        # Initialize Video Managers
        self.main_video_manager = VideoManager(
            video_url=f"http://{config['main_video_host']}:{main_video_port}/video",
            label=self.main_video_label
        )
        self.secondary_video_manager = VideoManager(
            video_url=f"http://{config['secondary_video_host']}:{secondary_video_port}/video",
            label=self.secondary_video_label
        )

        # Connect signals
        self.main_video_manager.frame_ready.connect(self.main_video_manager.display_frame)
        self.secondary_video_manager.frame_ready.connect(self.secondary_video_manager.display_frame)

        # Start video streams
        self.main_video_manager.start()
        self.secondary_video_manager.start()

    def closeEvent(self, event):
        """Stop video managers and close the app."""
        self.main_video_manager.stop()
        self.secondary_video_manager.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RemoteDrivingApp()
    window.show()
    sys.exit(app.exec_())


    window.show()
    sys.exit(app.exec_())

