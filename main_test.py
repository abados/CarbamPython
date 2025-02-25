import sys
import cv2
import serial
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QWidget, QGridLayout
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from control import Controll
from log_popup import LogPopup
from config import import_config

# Load the configuration
config = import_config()

# Access configuration variables
main_video_port = config.get("main_video_port", 0)  # Default to camera 0
secondary_video_port = config.get("secondary_video_port", None)
arduino_port = config.get("arduino_port", None)
resolution = config.get("resolution", (640, 480))
fps = config.get("fps", 30)

print(f"Main Video Port: {main_video_port}")
print(f"Secondary Video Port: {secondary_video_port}")
print(f"Arduino Port: {arduino_port}")


class RemoteDrivingApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Remote Driving System")
        self.setGeometry(100, 100, 1024, 768)
        # Main layout
        self.central_widget = QWidget()
        self.main_layout = QGridLayout()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        # Initialize Controll
        self.controls = Controll(self)
        self.main_layout.addWidget(self.controls, 0, 0, 1, 1)  # Add Controll to the layout

        # Focus policy
        self.controls.setFocusPolicy(Qt.StrongFocus)
        self.controls.setFocus()

        # Initialize variables
        self.serial_connection = None
        self.video_capture = None
        self.secondary_video_capture = None

        self.arm_status = False
        self.gear_value = "N"

        # Log window
        self.log_window = LogPopup(self)

        # Initialize UI
        self.setup_ui()

        # Initialize Controll class
        self.controls = Controll(self)

        # Check Arduino connection
        self.check_arduino_connection()

        # Start the main video stream
        self.start_video_stream()

    def setup_ui(self):
        """Setup the user interface."""
        # Main layout
        self.central_widget = QWidget()
        self.central_widget.setFocusPolicy(Qt.StrongFocus)  # Ensure keyboard focus
        self.main_layout = QGridLayout()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        # Video display
        self.video_label = QLabel("Main Video")
        self.video_label.setStyleSheet("background-color: black; color: white; font-size: 20px;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.video_label, 0, 1, 4, 4)

        # Gear status
        self.gear_status_label = QLabel("Current Gear: N")
        self.gear_status_label.setStyleSheet("font-size: 16px; color: black;")
        self.main_layout.addWidget(self.gear_status_label, 5, 1)

        # ARM/DISARM button
        self.arm_button = QPushButton("ARM/DISARM")
        self.arm_button.setStyleSheet("background-color: orange; font-size: 14px;")
        self.arm_button.clicked.connect(self.toggle_arm)
        self.main_layout.addWidget(self.arm_button, 2, 0)

        self.arm_status_label = QLabel("DISARMED")
        self.arm_status_label.setStyleSheet("color: red; font-size: 16px;")
        self.main_layout.addWidget(self.arm_status_label, 2, 1)

        # Secondary camera toggle
        self.show_secondary_button = QPushButton("Show Other Camera")
        self.show_secondary_button.setStyleSheet("background-color: lightgreen; font-size: 14px;")
        self.show_secondary_button.clicked.connect(self.toggle_secondary_camera)
        self.main_layout.addWidget(self.show_secondary_button, 5, 0)

        # Log button
        self.log_button = QPushButton("Show Log")
        self.log_button.setStyleSheet("background-color: lightblue; font-size: 14px;")
        self.log_button.clicked.connect(self.show_log_window)
        self.main_layout.addWidget(self.log_button, 4, 0)

    def toggle_arm(self):
        """Toggle ARM/DISARM state."""
        self.arm_status = not self.arm_status
        if self.arm_status:
            self.arm_status_label.setText("ARMED")
            self.arm_status_label.setStyleSheet("color: green; font-size: 16px;")
            self.log_message("System ARMED")
        else:
            self.arm_status_label.setText("DISARMED")
            self.arm_status_label.setStyleSheet("color: red; font-size: 16px;")
            self.log_message("System DISARMED")

        if self.serial_connection:
            try:
                self.serial_connection.write(f"ARM:{int(self.arm_status)}\n".encode())
            except Exception as e:
                self.log_message(f"Error sending ARM command: {e}")

    def set_gear(self, gear):
        """Set the current gear."""
        self.gear_value = gear
        self.gear_status_label.setText(f"Current Gear: {self.gear_value}")
        self.log_message(f"Gear changed to: {gear}")

    def log_message(self, message):
        """Log a message in the log window."""
        self.log_window.log_message(message)

    def show_log_window(self):
        """Show the log window."""
        self.log_window.show()

    def check_arduino_connection(self):
        """Check and establish the Arduino connection."""
        try:
            self.serial_connection = serial.Serial(arduino_port, baudrate=9600, timeout=1)
            self.log_message("Arduino connected successfully.")
        except Exception as e:
            self.log_message(f"Failed to connect to Arduino: {e}")

    def start_video_stream(self):
        """Start the main video stream."""
        self.video_capture = cv2.VideoCapture(main_video_port)
        if not self.video_capture.isOpened():
            self.log_message("Failed to open main video stream.")
            return

        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        self.video_capture.set(cv2.CAP_PROP_FPS, fps)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_video_stream)
        self.timer.start(1000 // fps)

    def update_video_stream(self):
        """Update the main video stream."""
        ret, frame = self.video_capture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized_frame = cv2.resize(frame, (self.video_label.width(), self.video_label.height()))
            height, width, channel = resized_frame.shape
            qimg = QImage(resized_frame.data, width, height, channel * width, QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(qimg))
        else:
            self.video_label.setText("No Video")
            self.log_message("Error reading video stream.")

    def toggle_secondary_camera(self):
        """Toggle the secondary camera feed."""
        if self.secondary_video_capture:
            self.secondary_video_capture.release()
            self.log_message("Secondary camera feed stopped.")
        else:
            self.secondary_video_capture = cv2.VideoCapture(secondary_video_port)
            if not self.secondary_video_capture.isOpened():
                self.log_message("Failed to open secondary video stream.")
            else:
                self.log_message("Secondary camera feed started.")

    def closeEvent(self, event):
        """Handle cleanup on application close."""
        if self.timer.isActive():
            self.timer.stop()
        if self.video_capture:
            self.video_capture.release()
        if self.secondary_video_capture:
            self.secondary_video_capture.release()
        if self.serial_connection:
            self.serial_connection.close()
        self.log_message("Application closed.")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RemoteDrivingApp()
    window.show()
    sys.exit(app.exec_())
