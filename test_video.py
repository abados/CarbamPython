import sys
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QPushButton, QWidget
from PyQt5.QtCore import Qt
from video4 import VideoManager


class VideoStreamApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Stream App")
        self.setGeometry(100, 100, 800, 600)

        # Initialize the QLabel to display video frames
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("Video Stream")
        self.video_label.setStyleSheet("background-color: black;")

        # Buttons for starting and stopping the video stream
        self.start_button = QPushButton("Start Stream", self)
        self.start_button.clicked.connect(self.start_stream)

        self.stop_button = QPushButton("Stop Stream", self)
        self.stop_button.clicked.connect(self.stop_stream)
        self.stop_button.setEnabled(False)  # Disable stop button initially

        # Layout for the GUI
        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        self.setLayout(layout)

        # Initialize the VideoManager
        self.video_manager = None
        self.rtsp_url = "http://192.168.1.101:8081"  # Replace with your RTSP URL

    def start_stream(self):
        """Starts the video stream."""
        if not self.video_manager:
            self.video_manager = VideoManager(self.rtsp_url, self.video_label)
            self.video_manager.frame_ready.connect(self.update_frame)
            self.video_manager.connection_lost.connect(self.handle_disconnection)
            self.video_manager.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_stream(self):
        """Stops the video stream."""
        if self.video_manager:
            self.video_manager.stop()
            self.video_manager.wait()  # Ensure the thread completes before proceeding
            self.video_manager = None
        self.video_label.setText("Video Stream")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def update_frame(self, frame):
        """Updates the QLabel with the latest video frame."""
        self.video_manager.display_frame(frame)

    def handle_disconnection(self):
        """Handles video stream disconnection."""
        self.stop_stream()
        self.video_label.setText("Connection Lost. Click Start to Reconnect.")

    def closeEvent(self, event):
        """Ensures proper cleanup when the application is closed."""
        if self.video_manager:
            self.video_manager.stop()

            self.video_manager = None
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoStreamApp()
    window.show()
    sys.exit(app.exec_())
