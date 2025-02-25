import sys
import cv2
import socket
import os
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


# Load the configuration
config = import_config()

# Access the variables
main_video_port = config["main_video_port"]
secondary_video_port = config["sacandary_video_port"]
arduino_ip = config["arduino_ip"]  # Arduino IP address
arduino_port = int(config["arduino_socket_port"])  # Arduino socket port

print(f"Main Video Port: {main_video_port}")
print(f"Secondary Video Port: {secondary_video_port}")
print(f"Arduino IP: {arduino_ip}")
print(f"Arduino Socket Port: {arduino_port}")
steering_factor = 3
from threading import Thread

class VideoCaptureThread(Thread):
    def __init__(self, capture, callback):
        super().__init__()
        self.capture = capture
        self.callback = callback
        self.running = True

    def run(self):
        while self.running and self.capture.isOpened():
            ret, frame = self.capture.read()
            if ret:
                self.callback(frame)

    def stop(self):
        self.running = False

class RemoteDrivingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.Joystick = RCSimulator()
        self.min_steering = int(config["min_steering"])
        self.max_steering = int(config["max_steering"])
        self.min_fuel = int(config["min_fuel"])
        self.max_fuel = int(config["max_fuel"])
        self.min_brake = int(config["min_brake"])
        self.max_brake = int(config["max_brake"])
        self.gear_arduino_value = ast.literal_eval(config["gear_arduino_value"])

        self.fuel_multiplier = float(config["fuel_multiplier"])  # Initial multiplier for fuel
        self.brake_multiplier = float(config["brake_multiplier"])  # Initial multiplier for brake
        self.steering_multiplier = float(config["fuel_multiplier"])  # Initial multiplier for steering

        self.setWindowTitle("Remote Driving System")
        self.setGeometry(100, 100, 1024, 768)

        # Initialize variables
        self.socket_connection = None
        self.video_capture = None
        self.secondary_video_capture = None

        # Poll joystick input
        self.joystick_timer = QTimer()
        self.joystick_timer.timeout.connect(self.update_from_joystick)
        self.joystick_timer.start(50)  # Poll joystick every 50 ms

        self.arm_status = False
        self.arm_pressed = False

        self.steering_speed = 0
        self.fuel_speed = 0
        self.brake_speed = 0
        self.gear_value = "N"
        self.gear_value_number = 0
        self.keys_pressed = set()  # Track pressed keys

        # Reset flags
        self.fuel_reset_enable = False
        self.brake_reset_enable = False
        self.steering_reset_enable = False

        # Aspect ratio
        self.video_aspect_ratio = 4 / 3

        # Secondary camera window
        self.secondary_window = QLabel("Secondary Camera")
        self.secondary_window.setStyleSheet("background-color: black; color: white; font-size: 16px;")
        self.secondary_window.setWindowTitle("Secondary Camera Feed")
        self.secondary_window.setGeometry(200, 200, 320, 240)  # Default size for the secondary window
        self.secondary_window.hide()  # Hide by default

        # Secondary camera timer
        self.secondary_timer = QTimer()
        self.secondary_timer.timeout.connect(self.update_secondary_video_stream)

        # Log window
        self.log_window = LogPopup(self)

        # Timers
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_video_stream)

        self.control_timer = QTimer()
        self.control_timer.timeout.connect(self.process_keys)  # Continuously process keys
        self.control_timer.start(20)  # Update every 20ms

        self.vector_timer = QTimer()
        self.vector_timer.timeout.connect(self.send_all_motor_values)
        self.arduino_update_ms_rate = int(config["arduino_update_ms_rate"])
        self.vector_timer.start(self.arduino_update_ms_rate)  # Send data every 100 ms

        # Layouts

        self.central_widget = QWidget()
        self.central_widget.setFocusPolicy(Qt.StrongFocus)  # Ensure keyboard focus
        self.main_layout = QGridLayout()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        # Video display
        self.video_label = QLabel("Main Video")
        self.video_label.setStyleSheet("background-color: blue; color: yellow; font-size: 20px;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.video_label, 0, 1, 4, 4)

        # Sliders and controls
        self.fuel_slider = self.create_vertical_slider("Fuel (motor 3)", 0, 0, self.on_fuel_slider_change)

        self.brake_slider = self.create_vertical_slider("Brake (motor 2)", 1, 0, self.on_brake_slider_change)
        self.steering_slider = self.create_horizontal_slider("Steering (motor 1)", 4, 1, 4, self.on_steering_slider_change)

        # Gear status display
        self.gear_status_label = QLabel("Current Gear: N")
        self.gear_status_label.setStyleSheet("font-size: 16px; color: black;")
        self.main_layout.addWidget(self.gear_status_label, 5, 1)

        # ARM/DISARM button and status
        self.arm_button = QPushButton("ARM/DISARM")
        self.arm_button.setStyleSheet("background-color: orange; font-size: 14px;")
        self.arm_button.clicked.connect(self.toggle_arm)
        self.main_layout.addWidget(self.arm_button, 2, 0)

        self.arm_status_label = QLabel("DISARMED")
        self.arm_status_label.setStyleSheet("color: red; font-size: 16px;")
        self.main_layout.addWidget(self.arm_status_label, 2, 1)

        # Arduino connection status
        self.arduino_status_label = QLabel("Arduino Not Connected")
        self.arduino_status_label.setStyleSheet("color: red; font-size: 16px;")
        self.main_layout.addWidget(self.arduino_status_label, 6, 0, 1, 2)

        # Log button
        self.log_button = QPushButton("Show Log")
        self.log_button.setStyleSheet("background-color: lightblue; font-size: 14px;")
        self.log_button.clicked.connect(self.show_log_window)
        self.main_layout.addWidget(self.log_button, 4, 0)

        # Show Other Camera button
        self.show_secondary_button = QPushButton("Show Other Camera")
        self.show_secondary_button.setStyleSheet("background-color: lightgreen; font-size: 14px;")
        self.show_secondary_button.clicked.connect(self.toggle_secondary_camera)
        self.main_layout.addWidget(self.show_secondary_button, 5, 0)

        # Check Arduino connection
        self.check_socket_connection()

        # Start timers
        self.start_video_stream()

    def create_vertical_slider(self, label, row, col, callback):
        layout = QVBoxLayout()
        slider = QSlider(Qt.Vertical)
        slider.setRange(0, 100)
        slider.setValue(0)
        slider.setFocusPolicy(Qt.StrongFocus)
        slider.valueChanged.connect(callback)
        layout.addWidget(QLabel(label))
        layout.addWidget(slider)
        self.main_layout.addLayout(layout, row, col)
        return slider

    def create_horizontal_slider(self, label, row, col_start, col_span, callback):
        layout = QVBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(-500, 500)
        slider.setValue(0)
        slider.setFocusPolicy(Qt.StrongFocus)
        slider.valueChanged.connect(callback)
        layout.addWidget(QLabel(label))
        layout.addWidget(slider)
        self.main_layout.addLayout(layout, row, col_start, 1, col_span)
        return slider

    def update_from_joystick(self):
        # Poll joystick
        channel_values = self.Joystick.poll_joystick()
        if self.Joystick.Joystick_conected:
            if channel_values[4]>1500 and channel_values[5]>1500:
                arm_value = 1
                self.arm_status = True
                self.arm_status_label.setText("ARMED")
                self.arm_status_label.setStyleSheet("color: green; font-size: 16px;")
            else:
                arm_value = 0
                self.arm_status = False
                self.arm_status_label.setText("DISARMED")
                self.arm_status_label.setStyleSheet("color: red; font-size: 16px;")

            # Update sliders based on joystick channel values
            # Map Channel 1 (steering) to horizontal slider (-500 to 500)
            self.steering_slider.setValue(int(np.interp(channel_values[0], [1200, 1800], [-500, 500])))

            if channel_values[2]>1500:
            # Map Channel 2 (fuel) to vertical slider (0 to 100)
                self.fuel_slider.setValue(int(np.interp(channel_values[2], [1500, 1800], [0, 100])))
                self.brake_slider.setValue(100)
            else:
                # Map Channel 3 (brake) to vertical slider (0 to 100)
                self.fuel_slider.setValue(0)
                self.brake_slider.setValue(int(np.interp(channel_values[2], [1200, 1500], [0, 100])))

    def keyPressEvent(self, event):
        self.keys_pressed.add(event.key())

    def keyReleaseEvent(self, event):
        if event.key() in self.keys_pressed:
            self.keys_pressed.remove(event.key())

    def process_keys(self):
        """Handle simultaneous key presses and reset logic."""


        if Qt.Key_D in self.keys_pressed:  # Increase fuel
            self.set_gear("D")
            self.gear_value_number = 1
        if Qt.Key_R in self.keys_pressed:  # Increase fuel
            self.set_gear("R")
            self.gear_value_number = 2
        if Qt.Key_N in self.keys_pressed:  # Increase fuel
            self.set_gear("N")
            self.gear_value_number = 0
        if Qt.Key_P in self.keys_pressed:  # Increase fuel
            self.set_gear("P")
            self.gear_value_number = 3
        if not self.Joystick.Joystick_conected:
            if Qt.Key_Q in self.keys_pressed:  # Increase fuel
                if not self.arm_pressed:
                    self.toggle_arm()
                    self.arm_pressed = True
            else:
                self.arm_pressed = False

        if Qt.Key_A in self.keys_pressed:  # Increase fuel
            self.brake_slider.setValue(min(self.brake_slider.value() + 2, self.brake_slider.maximum()))
            if self.brake_slider.value()>99:
                self.fuel_slider.setValue(min(self.fuel_slider.value() + 3 , self.fuel_slider.maximum()))
            self.fuel_reset_enable = False
        else:
            self.fuel_reset_enable = False

        if Qt.Key_Z in self.keys_pressed:  # Increase brake
            self.fuel_slider.setValue(min(self.fuel_slider.value() - 3 , self.fuel_slider.maximum()))
            if self.fuel_slider.value()<1:
                self.brake_slider.setValue(min(self.brake_slider.value() - 2, self.brake_slider.maximum()))
            self.brake_reset_enable = False
        else:
            self.brake_reset_enable = False

        if Qt.Key_Left in self.keys_pressed:  # Decrease steering
            step = int(np.interp(abs(self.steering_slider.value()), [0, 500], [5, 8]))  # Convert step to integer
            self.steering_slider.setValue(max(self.steering_slider.value() - step, self.steering_slider.minimum()))

        if Qt.Key_Right in self.keys_pressed:  # Increase steering
            step = int(np.interp(self.steering_slider.value(), [0, 500], [5, 8]))  # Convert step to integer
            self.steering_slider.setValue(min(self.steering_slider.value() + step, self.steering_slider.maximum()))

        # Set steering_reset_enable to True only when neither key is pressed
        self.steering_reset_enable = not (Qt.Key_Left in self.keys_pressed or Qt.Key_Right in self.keys_pressed)
        if Qt.Key_Down in self.keys_pressed:
            self.steering_reset_enable = False




        if not self.Joystick.Joystick_conected:

            # Reset logic for fuel
            if self.fuel_reset_enable and Qt.Key_Up not in self.keys_pressed:
                if self.fuel_slider.value() > 0:
                    self.fuel_slider.setValue(self.fuel_slider.value() - 4)
                else:
                    self.fuel_reset_enable = False

            # Reset logic for brake
            if self.brake_reset_enable and Qt.Key_Down not in self.keys_pressed:
                if self.brake_slider.value() > 0:
                    self.brake_slider.setValue(self.brake_slider.value() - 2)
                else:
                    self.brake_reset_enable = False

            # Reset logic for steering
            if self.steering_reset_enable:
                if abs(self.steering_slider.value())>15:
                    if self.steering_slider.value() < 0:
                        self.steering_slider.setValue(0)
                        # self.steering_slider.setValue(self.steering_slider.value() + 30)


                    elif self.steering_slider.value() > 0:
                        # self.steering_slider.setValue(self.steering_slider.value() - 30)
                        self.steering_slider.setValue(0)

                    else:
                        self.steering_reset_enable = False
                else:
                    if self.steering_slider.value() < 0:
                        self.steering_slider.setValue(self.steering_slider.value() + 1)
                    elif self.steering_slider.value() > 0:
                        self.steering_slider.setValue(self.steering_slider.value() - 1)
                    else:
                        self.steering_reset_enable = False



    def on_brake_slider_change(self, value):
        pass
        self.brake_speed = value
        # self.log_message(f"brake value: {np.interp(value, [0, 100], [1000, 2000])}")
        # self.send_to_arduino(2, np.interp(value, [0, 100], [1000, 2000]))  # Send brake value to motor 2

    def on_fuel_slider_change(self, value):
        pass
        self.fuel_speed = value
        # self.log_message(f"fuel value: {np.interp(value, [0, 100], [1000, 2000])}")
        # self.send_to_arduino(3, np.interp(value, [0, 100], [1000, 2000]))  # Send fuel value to motor 3

    def on_steering_slider_change(self, value):
        pass
        self.steering_speed = value
        # self.log_message(f"steering value: {np.interp(value, [-500, 500], [1000, 2000])}")
        #
        # self.send_to_arduino(1, np.interp(value, [-500, 500], [1000, 2000]) )  # Send steering value to motor 1

    def log_message(self, message):
        self.log_window.log_message(message)


    def show_log_window(self):
        self.log_window.show()



    def send_arm_status(self):
        arm_value = 1 if self.arm_status else 0
        self.send_to_arduino(6, arm_value)

    def toggle_arm(self):
        self.arm_status = not self.arm_status
        arm_value = 1 if self.arm_status else 0
        if self.arm_status:
            self.arm_status_label.setText("ARMED")
            self.arm_status_label.setStyleSheet("color: green; font-size: 16px;")
            self.log_message("System ARMED")
        else:
            self.arm_status_label.setText("DISARMED")
            self.arm_status_label.setStyleSheet("color: red; font-size: 16px;")
            self.log_message("System DISARMED")
            self.update_config_file()

        # Send ARM/DISARM status via socket
        self.send_to_arduino(6, arm_value)



    def check_socket_connection(self):
        try:
            self.socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_connection.settimeout(10)
            self.socket_connection.connect((arduino_ip, arduino_port))
            self.arduino_status_label.setText("Arduino Connected")
            self.arduino_status_label.setStyleSheet("color: green; font-size: 16px;")
            self.log_message("Arduino connected successfully via socket.")
        except Exception as e:
            self.arduino_status_label.setText("Arduino Not Connected")
            print("Arduino Not Connected")
            self.arduino_status_label.setStyleSheet("color: red; font-size: 16px;")
            self.log_message(f"Failed to connect to Arduino via socket: {e}")
            print(f"Failed to connect to Arduino via socket: {e}")
    def send_to_arduino(self, motor_id, value):
        """
        Send a command to the Arduino server in the format 'motorID:value'.
        """
        if self.socket_connection:
            try:
                command = f"{motor_id}:{value}\n"
                self.socket_connection.sendall(command.encode())
                self.log_message(f"Sent to Arduino: {command}")
            except Exception as e:
                self.log_message(f"Error sending command to Arduino: {e}")
        else:
            self.log_message("Socket connection to Arduino not established.")

        def check_socket_connection(self):
            try:
                self.socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket_connection.connect((arduino_ip, arduino_port))
                self.arduino_status_label.setText("Arduino Connected")
                self.arduino_status_label.setStyleSheet("color: green; font-size: 16px;")
                self.log_message("Arduino connected successfully via socket.")
            except Exception as e:
                self.arduino_status_label.setText("Arduino Not Connected")
                self.arduino_status_label.setStyleSheet("color: red; font-size: 16px;")
                self.log_message(f"Failed to connect to Arduino via socket: {e}")

    def send_all_motor_values(self):
        """Send all motor values and fail-safe state to the Arduino as a vector."""
        if self.socket_connection:
            try:
                steering_value = np.interp(self.steering_slider.value(), [-500, 500], [self.min_steering, self.max_steering])
                if steering_value>1500:
                    steering_value=steering_value+250
                if 1500>steering_value:
                    steering_value=steering_value-250
                fuel_value = np.interp(self.fuel_slider.value(), [0, 100], [self.min_fuel, self.max_fuel])
                brake_value = np.interp(self.brake_slider.value(), [0, 100], [self.max_brake, self.min_brake])
                gear_value = self.gear_arduino_value[self.gear_value_number]
                arm_value = 1 if self.arm_status else 0

                vector_message = f"[{steering_value:.0f},{brake_value:.0f},{fuel_value:.0f},{gear_value:.0f},{arm_value}]\n"
                self.socket_connection.sendall(vector_message.encode())
                self.log_message(f"Sent to Arduino: {vector_message}")
            except Exception as e:
                self.log_message(f"Error sending data to Arduino: {e}")
        else:
            self.log_message("Socket connection to Arduino not established.")


    def start_video_stream(self):
        # Replace 'main_video_port' with the URL of your main video stream
        self.video_capture = cv2.VideoCapture(f"http://{config['main_video_host']}:{main_video_port}/video")

        if not self.video_capture.isOpened():
            self.log_message("Failed to open main video stream.")
            return

        self.video_thread = VideoCaptureThread(self.video_capture, self.process_frame)
        self.video_thread.start()


    def process_frame(self, frame):
        # Process the frame for display
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized_frame = cv2.resize(frame, (self.video_label.width(), self.video_label.height()))
        height, width, channel = resized_frame.shape
        qimg = QImage(resized_frame.data, width, height, channel * width, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qimg))


    def update_video_stream(self):
        start_time = time.time()  # Capture the start time of frame processing

        # Clear frame buffer to process the latest frame
        while self.video_capture.isOpened() and self.video_capture.grab():
            pass

        ret, frame = self.video_capture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Calculate latency
            latency = int((time.time() - start_time) * 1000)  # Latency in milliseconds

            # Add latency as text overlay
            cv2.putText(frame, f"Latency: {latency} ms", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

            resized_frame = cv2.resize(frame, (self.video_label.width(), self.video_label.height()))
            height, width, channel = resized_frame.shape
            qimg = QImage(resized_frame.data, width, height, channel * width, QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(qimg))
        else:
            self.video_label.setText("No Video")
            self.log_message("Video stream failed.")

    def update_secondary_video_stream(self):
        start_time = time.time()  # Capture the start time of frame processing
        if self.secondary_video_capture:
            ret, frame = self.secondary_video_capture.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Calculate latency
                latency = int((time.time() - start_time) * 1000)  # Latency in milliseconds

                # Add latency as text overlay
                cv2.putText(frame, f"Latency: {latency} ms", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

                height, width, channel = frame.shape
                qimg = QImage(frame.data, width, height, channel * width, QImage.Format_RGB888)
                self.secondary_window.setPixmap(QPixmap.fromImage(qimg))
            else:
                self.secondary_window.setText("No Video")
                self.log_message("Secondary camera stream failed.")

    def set_gear(self, gear):
        """Set the current gear."""
        self.gear_value = gear
        self.gear_status_label.setText(f"Current Gear: {self.gear_value}")
        self.log_message(f"Gear changed to: {gear}")

    def toggle_secondary_camera(self):
        if self.secondary_window.isVisible():
            self.secondary_window.hide()
            self.secondary_timer.stop()
            if self.secondary_video_capture:
                self.secondary_video_capture.release()
            self.log_message("Secondary camera feed closed.")
        else:
            # Initialize secondary video capture
            self.secondary_video_capture = cv2.VideoCapture(f"http://{config['secondary_video_host']}:{config['secondary_video_port']}/video")

            # Check if the stream opens successfully
            if self.secondary_video_capture.isOpened():
                self.secondary_window.show()
                self.secondary_timer.start(30)  # Update every 30ms
                self.log_message("Secondary camera feed started.")
            else:
                self.secondary_window.setText("Failed to open secondary camera")
                self.log_message("Failed to open secondary camera.")
                print(f"Failed to open secondary camera: http://{config['secondary_video_host']}:{config['secondary_video_port']}/video")


    def resizeEvent(self, event):
        available_width = self.central_widget.width() - 200
        available_height = self.central_widget.height() - 200
        if available_width / available_height > self.video_aspect_ratio:
            new_height = available_height
            new_width = int(new_height * self.video_aspect_ratio)
        else:
            new_width = available_width
            new_height = int(new_width / self.video_aspect_ratio)

        self.video_label.setFixedSize(new_width, new_height)
        super().resizeEvent(event)

    def update_controls(self):
        pass

    def update_config_file(self):
        print("config updated")
        config = import_config()
        self.min_steering = int(config["min_steering"])
        self.max_steering = int(config["max_steering"])
        self.min_fuel = int(config["min_fuel"])
        print(self.min_fuel)

        self.max_fuel = int(config["max_fuel"])
        self.min_brake = int(config["min_brake"])
        self.max_brake = int(config["max_brake"])
        self.gear_arduino_value = ast.literal_eval(config["gear_arduino_value"])

        self.fuel_multiplier = float(config["fuel_multiplier"])  # Initial multiplier for fuel
        self.brake_multiplier = float(config["brake_multiplier"])  # Initial multiplier for brake
        self.steering_multiplier = float(config["fuel_multiplier"])  # Initial multiplier for brake

    def closeEvent(self, event):
        if self.timer.isActive():
            self.timer.stop()
        if self.vector_timer.isActive():
            self.vector_timer.stop()
        if self.video_capture:
            self.video_capture.release()
        if self.secondary_video_capture:
            self.secondary_video_capture.release()
        if self.socket_connection:
            self.socket_connection.close()
        self.log_message("Application closed.")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RemoteDrivingApp()
    window.show()
    sys.exit(app.exec_())


    window.show()
    sys.exit(app.exec_())

