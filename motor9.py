from PTZ_control import PTZCameraController
import sys
import threading
import cv2
import socket
import os
import logging
import pygame
import ast
import time  # For latency calculationX
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QSlider,
    QPushButton, QWidget, QGridLayout,QTextEdit
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
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
print(main_video_port)
print(secondary_video_port)

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

        self.PTZ_controller = PTZCameraController("192.168.1.64", 8000, "OnvifUser", "a1s2d3f4")

        self.setWindowTitle("Remote Driving System")
        self.setGeometry(100, 100, 1500, 900)

        # Main widget and layout
        self.central_widget = QWidget()
        self.main_layout = QGridLayout()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)



        self.path_to_save_video = config["path_to_save_video"]
        self.is_recording = False  # Flag to track recording status
        self.video_writer = None  # OpenCV VideoWriter object

        self.Joystick = RCSimulator()
        self.min_steering = int(config["min_steering"])
        self.max_steering = int(config["max_steering"])
        self.min_fuel = int(config["min_fuel"])
        self.max_fuel = int(config["max_fuel"])
        self.fuel_offset = int(config["fuel_offset"])
        self.fuel_slide_update_rate = int(config["fuel_slide_update_rate"])
        self.brake_slide_update_rate = int(config["brake_slide_update_rate"])
        self.arduino_ip= (config["arduino_ip"])
        self.arduino_socket_port= (config["arduino_socket_port"])
        self.gear_P_arduino_value = int(config["gear_P_arduino_value"])
        self.gear_D_arduino_value = int(config["gear_D_arduino_value"])
        self.gear_N_arduino_value = int(config["gear_N_arduino_value"])
        self.gear_R_arduino_value = int(config["gear_R_arduino_value"])
        self.min_brake = int(config["min_brake"])
        self.max_brake = int(config["max_brake"])
        self.fuel_multiplier = float(config["fuel_multiplier"])  # Initial multiplier for fuel
        self.brake_multiplier = float(config["brake_multiplier"])  # Initial multiplier for brake
        self.steering_multiplier = float(config["fuel_multiplier"])  # Initial multiplier for steering
        self.steering_TH = float(config["steering_TH"])  # Initial multiplier for steering
        self.fuel_auto_reset =  int(config["fuel_auto_reset"])  # Initial multiplier for steering
        # Poll joystick input
        self.joystick_timer = QTimer()
        try:
            #self.joystick_timer.timeout.connect(self.update_from_joystick)
            pass
        except Exception as e:
            logging.error(f"Error during joystick_timer: {e}")
            self.log_message(f"Error during joystick_timer: {e}")

        self.joystick_timer.start(50)  # Poll joystick every 50 ms

        self.arm_status = False
        self.arm_pressed = False

        self.steering_speed = 0
        self.fuel_speed = 0
        self.brake_speed = 0
        self.gear_value = "N"
        self.gear_value_number = 0
        self.keys_pressed = set()  # Track pressed keys
        self.steering_dir = 2
        # Reset flags
        self.fuel_reset_enable = False
        self.brake_reset_enable = False
        self.steering_reset_enable = False


        pygame.init()
        pygame.joystick.init()
        self.control_timer = QTimer()
        try:
            if self.detect_joystick():
                self.control_timer.timeout.connect(self.process_joystick_keys)
            else:
                self.control_timer.timeout.connect(self.process_keys)  # Continuously process keys
        except Exception as e:
            logging.error(f"Error occurred: {e}")
            self.log_message(f"Error occurred: {e}")
        self.control_timer.start(20)  # Update every 20ms

        self.vector_timer = QTimer()
        try:
            self.vector_timer.timeout.connect(self.send_all_motor_values)
        except Exception as e:
            logging.error(f"Error during vector_timer: {e}")
            self.log_message(f"Error during vector_timer: {e}")

        self.arduino_update_ms_rate = int(config["arduino_update_ms_rate"])
        self.vector_timer.start(self.arduino_update_ms_rate)  # Send data every 100 ms

        self.central_widget = QWidget()
        self.central_widget.setFocusPolicy(Qt.StrongFocus)  # Ensure keyboard focus
        self.main_layout = QGridLayout()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        # Add the log display widget
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)  # Make the log widget read-only
        self.log_display.setStyleSheet("font-size: 12px; color: black; background-color: #f0f0f0;")
        self.main_layout.addWidget(self.log_display, 0, 8, 8, 2)  # Add to the right side of the main layout





        self.fuel_slider = self.create_vertical_slider("Fuel (motor 3)", 0, 0, self.on_fuel_slider_change)

        self.brake_slider = self.create_vertical_slider("Brake (motor 2)", 1, 0, self.on_brake_slider_change)
        self.steering_slider = self.create_horizontal_slider("Steering (motor 1)", 4, 1, 4, self.on_steering_slider_change)

         # Gear status display
        self.gear_status_label = QLabel("Current Gear: N")
        self.gear_status_label.setStyleSheet("font-size: 16px; color: black;")
        self.main_layout.addWidget(self.gear_status_label, 5, 2)

        # ARM/DISARM button and status
        self.arm_button = QPushButton("ARM/DISARM")
        self.arm_button.setStyleSheet("background-color: orange; font-size: 14px;")
        self.arm_button.clicked.connect(self.toggle_arm)
        self.main_layout.addWidget(self.arm_button, 2, 0)
        self.arm_button = QPushButton("ARM/DISARM")

        self.previous_steering = None
        self.previous_brake = None
        self.previous_fuel = None
        self.previous_gear = None
        self.previous_arm = None
        self.connect_Arduino = QPushButton("connect arduino")
        self.connect_Arduino.setStyleSheet("background-color: orange; font-size: 14px;")
        self.connect_Arduino.clicked.connect(self.check_socket_connection)
        self.main_layout.addWidget(self.connect_Arduino, 4, 0)

        self.arm_status_label = QLabel("DISARMED")
        self.arm_status_label.setStyleSheet("color: red; font-size: 16px;")
        self.main_layout.addWidget(self.arm_status_label, 3, 0)

        self.arduino_status_label = QLabel("Arduino Not Connected")
        self.arduino_status_label.setStyleSheet("color: red; font-size: 16px;")
        self.main_layout.addWidget(self.arduino_status_label, 5, 0, 1, 2)
        # Create "Start/Stop Recording" button
        self.record_button = QPushButton("Start Recording")
        self.record_button.setStyleSheet("background-color: red; font-size: 14px;")
        self.record_button.clicked.connect(self.start_recording)
        self.main_layout.addWidget(self.record_button, 6, 1)  # Add button to layout
        # Log button
        self.log_button = QPushButton("Show Log")
        self.log_button.setStyleSheet("background-color: lightblue; font-size: 14px;")
        self.log_button.clicked.connect(self.show_log_window)
        self.main_layout.addWidget(self.log_button, 6, 2)
        self.kiebord_interupt = False


        # Initialize secondary video visibility state
        self.secondary_video_visible = True

        # Main video label
        self.main_video_label = QLabel("Main Video")
        self.main_video_label.setStyleSheet("background-color: black; color: yellow; font-size: 20px;")
        self.main_video_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.main_video_label, 0, 1, 4, 6)
        # Secondary video label
        self.secondary_video_label = QLabel("Secondary Video")
        self.secondary_video_label.setStyleSheet("background-color: gray; color: white; font-size: 16px;")
        self.secondary_video_label.setAlignment(Qt.AlignCenter)
        # self.main_layout.addWidget(self.secondary_video_label,  1, 4, 2, 3)  # Rows 0-1, Cols 4-5

        self.main_layout.addWidget(self.secondary_video_label,  1, 4, 0, 0)  # Rows 0-1, Cols 4-5


        self.video_manager = None
        self.start_stream(rtsp_url=f"{config['main_video_host']}",video_label=self.main_video_label)
        # self.main_video_manager = VideoManager(
        #     video_url="rtsp://192.168.1.111/camera1.sdp",
        #     label=self.main_video_label
        # )


        # Connect signals
        self.socket_connection = None

        # Start video streams
        self.reconnect_timer = QTimer()
        try:
            self.reconnect_timer.timeout.connect(self.check_socket_connection)
            logging.error(f"trying reconect arduino")
        except Exception as e:
            logging.error(f"Error occurred: {e}")
            self.log_message(f"Error occurred: {e}")
        self.reconnect_timer.start(1000)  # Try reconnecting every 5 seconds

        # Timer for recording frames
        try:
            self.recording_timer = QTimer()
            self.recording_timer.timeout.connect(self.capture_window_frame)
        except Exception as e:
            logging.error(f"Error during recording_timer: {e}")
            self.log_message(f"Error during recording_timer: {e}")

        self.add_ptz_controls()



    def toggle_secondary_video(self):
        """Show or stop the secondary video and resize the main video window."""
        if self.secondary_video_visible:
            # self.main_video_manager.stop()
            self.secondary_video_manager.stop()
            self.secondary_video_label.hide()  # Hide the video label
            self.toggle_secondary_video_button.setText("Show Secondary Video")
            self.toggle_secondary_video_button.hide()
            self.log_message("Secondary video stopped.")
            # Resize the main video label to occupy more space
            self.main_layout.addWidget(self.main_video_label, 0, 1, 4, 8)  # Extend to columns 1-6
            # self.main_video_manager.start()

        else:
            self.secondary_video_manager.start()
            self.secondary_video_label.show()  # Show the video label
            self.toggle_secondary_video_button.setText("Stop Secondary Video")
            self.log_message("Secondary video started.")

            # Reset the main video label size
            self.main_layout.addWidget(self.main_video_label, 0, 1, 4, 4)  # Reset to columns 1-4
        self.secondary_video_visible = not self.secondary_video_visible

    def add_ptz_controls(self):
        """Adds PTZ control buttons to the bottom-left corner of the video area."""
        # Create PTZ buttons
        self.up_button = QPushButton("↑", self)
        self.down_button = QPushButton("↓", self)
        self.left_button = QPushButton("←", self)
        self.right_button = QPushButton("→", self)
        self.zoom_in_button = QPushButton("+", self)  # Zoom in button
        self.zoom_out_button = QPushButton("−", self)  # Zoom out button

        # Style buttons to make them visually appealing
        button_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 150);
                border: 1px solid gray;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 200);
            }
        """
        for button in [self.up_button, self.down_button, self.left_button, self.right_button, self.zoom_in_button,
                       self.zoom_out_button]:
            button.setStyleSheet(button_style)
            button.setFixedSize(35, 35)

        # Create a layout for PTZ buttons
        ptz_layout = QVBoxLayout()
        ptz_layout.setSpacing(3)

        # Create a grid layout for the PTZ controls
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.up_button, 0, 1)  # Up button in the center
        grid_layout.addWidget(self.left_button, 1, 0)  # Left button
        grid_layout.addWidget(self.right_button, 1, 2)  # Right button
        grid_layout.addWidget(self.down_button, 2, 1)  # Down button
        grid_layout.addWidget(self.zoom_in_button, 1, 6)  # Zoom in button in the center
        grid_layout.addWidget(self.zoom_out_button, 2, 6)  # Zoom out button below the others

        # Create a widget for the PTZ controls
        ptz_widget = QWidget(self)
        ptz_widget.setLayout(grid_layout)
        ptz_widget.setStyleSheet("background: transparent;")  # Transparent background

        # Dynamically position the widget relative to the main video label
        def position_ptz_widget():
            ptz_widget.setGeometry(
                self.main_video_label.x() + 0,  # Offset from the left edge of the video
                self.main_video_label.y() + self.main_video_label.height() - 200,  # Offset from the bottom of the video
                160, 200  # Width and height of the PTZ controls
            )

        # Adjust position after the UI is fully loaded
        QTimer.singleShot(0, position_ptz_widget)

        # Connect buttons to PTZ commands
        self.up_button.clicked.connect(lambda: self.PTZ_controller.relative_move(0.0, 0.1))
        self.down_button.clicked.connect(lambda: self.PTZ_controller.relative_move(0.0, -0.1))
        self.left_button.clicked.connect(lambda: self.PTZ_controller.relative_move(-0.1, 0.0))
        self.right_button.clicked.connect(lambda: self.PTZ_controller.relative_move(0.1, 0.0))
        self.zoom_in_button.clicked.connect(lambda: self.PTZ_controller.relative_move(0, 0.0,0.1))  # Zoom in by a small step
        self.zoom_out_button.clicked.connect(lambda: self.PTZ_controller.relative_move(0, 0.0,-0.1))  # Zoom out by a small step

        # Save the PTZ widget for future reference
        self.ptz_widget = ptz_widget

    def start_stream(self, rtsp_url, video_label):
        """Starts the video stream."""
        self.rtsp_url = rtsp_url  # Save the URL for reconnection attempts
        self.main_video_label = video_label  # Save the label reference
        if not self.video_manager:
            self.video_manager = VideoManager(rtsp_url, video_label)
            self.video_manager.frame_ready.connect(self.update_frame)
            self.video_manager.connection_lost.connect(self.handle_disconnection)
        try:
            self.video_manager.start()
            self.log_message("Video stream started successfully.")
        except Exception as e:
            logging.error(f"Video stream error: {e}")
            self.log_message(f"Failed to start video stream: {e}")

    def update_frame(self, frame):
        """Updates the QLabel with the latest video frame."""
        try:
            self.video_manager.display_frame(frame)
        except Exception as e:
            logging.error(f"Frame capture/recording error: {e}")
            self.log_message(f"Error capturing or recording frame: {e}")
        # self.start_button.setEnabled(False)
        # self.stop_button.setEnabled(True)

    def handle_disconnection(self):
        """Handles video stream disconnection and attempts to reconnect."""
        logging.warning("Video stream disconnected. Attempting to reconnect...")
        self.log_message("Connection lost. Attempting to reconnect...")

        # Stop the current stream if it is running
        self.stop_stream()

        # Display message to the user
        self.main_video_label.setText("Connection Lost. Reconnecting...")

        # Attempt to reconnect after a delay
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self.try_reconnect)
        self.reconnect_timer.start(5000)  # Retry every 5 seconds

    def try_reconnect(self):
        """Attempts to reconnect to the video stream."""
        try:
            self.start_stream(self.rtsp_url, self.main_video_label)
            self.log_message("Reconnected successfully.")
            self.reconnect_timer.stop()  # Stop the timer if reconnection succeeds
        except Exception as e:
            logging.error(f"Reconnection attempt failed: {e}")
            self.log_message(f"Reconnection attempt failed. Retrying...")

    def stop_stream(self):
        """Stops the video stream."""

        if self.video_manager:
            self.video_manager.stop()
            self.video_manager.wait()  # Ensure the thread completes before proceeding
            self.video_manager = None
        self.main_video_label.setText("Video Stream")
        # self.start_button.setEnabled(True)
        # self.stop_button.setEnabled(False)

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
        import numpy as np
        def scale_joystick_input(value, center=1500, input_min=1100, input_max=1900, output_min=-500, output_max=500):
            # Shift the input around the center (1500)
            shifted_value = value - center

            # Normalize input to [-1, 1] around the center
            if shifted_value > 0:
                normalized_value = shifted_value / (input_max - center)
            else:
                normalized_value = shifted_value / (center - input_min)

            # Apply a nonlinear scaling (logarithmic-like)
            scaled_value = np.sign(normalized_value) * (np.abs(normalized_value) ** 2)  # Quadratic scaling

            # Map back to the desired output range
            return int(scaled_value * (output_max - output_min) / 2)

        # Poll joystick

        try:
            channel_values = self.Joystick.poll_joystick()
        except Exception as e:
            logging.error(f"Joystick polling error: {e}")
            self.log_message(f"Joystick polling error: {e}")
            self.Joystick.Joystick_conected = False
        if self.Joystick.Joystick_conected:
            # Check arming status based on channels 4 and 5

            if self.arm_status:
                if channel_values[4] < 1500 or channel_values[5] < 1500:
                    self.arm_status = False
                    self.arm_status_label.setText("DISARMED")
                    self.arm_status_label.setStyleSheet("color: red; font-size: 16px;")
                    self.fuel_slider.setValue(0)
                    self.brake_slider.setValue(0)

            else:
                if channel_values[4] > 1500 and channel_values[5] > 1500 and channel_values[2]<1200:
                    self.arm_status = True
                    self.arm_status_label.setText("ARMED")
                    self.arm_status_label.setStyleSheet("color: green; font-size: 16px;")

            if self.arm_status:
                # Set steering value with centered and balanced scaling
                if abs(channel_values[0] - 1500) < 30:
                    channel_values[0] = 1500
                self.steering_slider.setValue(scale_joystick_input(channel_values[0]))

                # Gradual update for fuel and brake sliders
                target_fuel = 0
                target_brake = 0

                if channel_values[2] > 1500:
                    target_fuel = int(np.interp(channel_values[2], [1500, 1800], [0, 100]))
                    target_brake = 100
                else:
                    target_fuel = 0
                    target_brake = int(np.interp(channel_values[2], [1200, 1500], [0, 100]))
                if (self.brake_slider.value() - target_brake)>75:
                    self.arm_status = False
                    self.arm_status_label.setText("DISARMED")
                    self.arm_status_label.setStyleSheet("color: red; font-size: 16px;")
                    self.fuel_slider.setValue(0)
                    self.brake_slider.setValue(0)

                # Gradual update for fuel slider
                if self.brake_slider.value()==100:
                    if self.fuel_slider.value() < target_fuel:
                        self.fuel_slider.setValue(min(self.fuel_slider.value() + self.fuel_slide_update_rate, target_fuel))
                    elif self.fuel_slider.value() > target_fuel:
                        self.fuel_slider.setValue(max(self.fuel_slider.value() - self.fuel_slide_update_rate, target_fuel))

                # Gradual update for brake slider
                if self.fuel_slider.value()==0:
                    if self.brake_slider.value() < target_brake:
                        self.brake_slider.setValue(min(self.brake_slider.value() + self.brake_slide_update_rate, target_brake))
                    elif self.brake_slider.value() > target_brake:
                        self.brake_slider.setValue(max(self.brake_slider.value() - self.brake_slide_update_rate, target_brake))
            if not self.kiebord_interupt:
                if  channel_values[6] == 1000:
                    self.set_gear("D")
                    self.gear_value_number = 1
                elif  channel_values[6] == 1500:
                    print("set gear to N")
                    self.set_gear("N")
                    self.gear_value_number = 0
                elif  channel_values[6] == 2000:
                    self.set_gear("R")
                    self.gear_value_number = 2

    def keyPressEvent(self, event):
        self.keys_pressed.add(event.key())

    def keyReleaseEvent(self, event):
        if event.key() in self.keys_pressed:
            self.keys_pressed.remove(event.key())

    def detect_joystick(self):
        if pygame.joystick.get_count() > 0:
            print("Found available Joystick")
            return True
        return False

    def process_joystick_keys(self):
        running = True
        while running and pygame.joystick.get_count() > 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.JOYAXISMOTION:
                    axis = event.axis  # Axis index
                    value = event.value  # Axis value (-1 to 1)
                    if axis == 0:  # Steering axis
                        print(f"Steering: {value:.3f}")
                    elif axis == 5:  # Accelerator
                        print(f"Accelerator: {value:.3f}")
                    elif axis == 1:  # Brake
                        print(f"Brake: {value:.3f}")
                elif event.type == pygame.JOYBUTTONDOWN:
                    print(f"Button {event.button} pressed")
                    pressed_button=event.button
                    if pressed_button==0:
                            print("Button 0 pressed")
                    elif pressed_button==1:
                            print("Button 1 pressed")
                    elif pressed_button==2:
                            print("Button 2 pressed")
                            self.set_gear("D")
                            self.gear_value_number = 1
                            self.kiebord_interupt = False
                            self.PTZ_controller.go_to_location(1)
                    elif pressed_button==3:
                            print("Button 3 pressed")
                            self.set_gear("N")
                            self.gear_value_number = 0
                            self.kiebord_interupt = False
                            self.PTZ_controller.go_to_location(3)
                    elif pressed_button==4: 
                            print("Button 4 pressed")
                            self.set_gear("P")
                            self.gear_value_number = 3
                            self.kiebord_interupt = True
                    elif pressed_button==5:
                            print("Button 5 pressed")
                            self.set_gear("R")
                            self.gear_value_number = 2
                            self.kiebord_interupt = False
                            self.PTZ_controller.go_to_location(2)
                    elif pressed_button==6:
                            print("Button 6 pressed")
                    elif pressed_button==7: 
                            print("Button 7 pressed")
                    elif pressed_button==8:
                            print("Button 8 pressed")
                            self.toggle_arm()
                            self.arm_pressed = not self.arm_pressed
                            self.fuel_slider.setValue(0)
                            self.brake_slider.setValue(0)
                    elif pressed_button==9:
                            print("Button 9 pressed")
                    elif pressed_button==10:
                            print("Button 10 pressed")
                    elif pressed_button==11:
                            print("Button 11 pressed")
                            self.send_all_motor_values()
                    elif pressed_button==12:
                            print("Button 12 pressed")
                            running=False
                    else:
                        print("Button Undefined Pressed")


                elif event.type == pygame.JOYHATMOTION:
                    print(f"Hat {event.hat} moved to {event.value}")

    #pygame.quit()

    def process_keys(self):
        """Handle simultaneous key presses and reset logic."""


        if Qt.Key_D in self.keys_pressed:  # Increase fuel
            self.set_gear("D")
            self.gear_value_number = 1
            self.kiebord_interupt = False
            self.PTZ_controller.go_to_location(1)

        if Qt.Key_R in self.keys_pressed:  # Increase fuel
            self.set_gear("R")
            self.gear_value_number = 2
            self.kiebord_interupt = False
            self.PTZ_controller.go_to_location(2)

            # self.stop_stream()
            # self.start_stream(rtsp_url=f"{config['secondary_video_host']}", video_label=self.main_video_label)

        if Qt.Key_N in self.keys_pressed:  # Increase fuel
            self.set_gear("N")
            self.gear_value_number = 0
            self.kiebord_interupt = False
            self.PTZ_controller.go_to_location(3)

        if Qt.Key_P in self.keys_pressed:  # Increase fuel
            self.set_gear("P")
            self.gear_value_number = 3
            self.kiebord_interupt = True
        if not self.Joystick.Joystick_conected:
            if Qt.Key_Q in self.keys_pressed:  # Increase fuel
                if not self.arm_pressed:
                    self.toggle_arm()
                    self.arm_pressed = True
                    self.fuel_slider.setValue(0)
                    self.brake_slider.setValue(0)

            else:
                self.arm_pressed = False
        if not Qt.Key_Down in self.keys_pressed:
            if self.fuel_slider.value() > 3:
                self.brake_slider.setValue(self.brake_slider.maximum())
            if Qt.Key_A in self.keys_pressed:  # Increase fuel
                self.brake_slider.setValue(min(self.brake_slider.value() + 2, self.brake_slider.maximum()))
                if self.brake_slider.value()>99 or Qt.Key_Down in self.keys_pressed:
                    self.fuel_slider.setValue(min(self.fuel_slider.value() + 3 , self.fuel_slider.maximum()))
                self.fuel_reset_enable = False
            else:
                self.fuel_reset_enable = False
                if self.brake_slider.value()>99:
                    if not Qt.Key_Up in self.keys_pressed:
                        self.fuel_slider.setValue(min(self.fuel_slider.value() - self.fuel_auto_reset , self.fuel_slider.maximum()))
        else:

            if Qt.Key_A in self.keys_pressed:  # Increase fuel
                self.brake_slider.setValue(min(self.brake_slider.value() + 0, self.brake_slider.maximum()))
                if self.brake_slider.value() > 99 or Qt.Key_Down in self.keys_pressed:
                    self.fuel_slider.setValue(min(self.fuel_slider.value() + 3, self.fuel_slider.maximum()))
                self.fuel_reset_enable = False

            else:
                self.fuel_reset_enable = False
                if not Qt.Key_Up in self.keys_pressed:
                    self.fuel_slider.setValue(min(self.fuel_slider.value() - 4, self.fuel_slider.maximum()))


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
            self.steering_dir = 0
        if Qt.Key_Right in self.keys_pressed:  # Increase steering
            step = int(np.interp(self.steering_slider.value(), [0, 500], [5, 8]))  # Convert step to integer
            self.steering_slider.setValue(min(self.steering_slider.value() + step, self.steering_slider.maximum()))
            self.steering_dir = 1
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
        """Log messages to the log display and save them to the log file."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} - {message}"
        self.log_display.append(log_entry)  # Append to the log display
        # logging.info(message)  # Log to the file
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
            # self.update_config_file()

        # Send ARM/DISARM status via socket
        self.send_to_arduino(6, arm_value)

    def check_socket_connection(self):
        if self.socket_connection:
            try:
                # Test connection by sending a small command (heartbeat)
                self.socket_connection.sendall(b"heartbeat\n")
                return  # Connection is active, no need to reconnect
            except:
                # If sending fails, assume connection is broken
                self.socket_connection.close()
                self.socket_connection = None
                self.arduino_status_label.setText("Arduino Not Connected")
                self.arm_status_label.setText("DISARMED")
                self.arm_status_label.setStyleSheet("color: red; font-size: 16px;")
                self.fuel_slider.setValue(0)
                self.brake_slider.setValue(0)
                self.arduino_status_label.setStyleSheet("color: red; font-size: 16px;")
                self.update_config_file()

        # Try reconnecting
        try:
            self.socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_connection.settimeout(2)
            self.socket_connection.connect((self.arduino_ip, self.arduino_socket_port))
            self.arduino_status_label.setText("Arduino Connected")
            self.arduino_status_label.setStyleSheet("color: green; font-size: 16px;")
            self.log_message("Arduino reconnected successfully.")
        except Exception as e:
            self.arduino_status_label.setText("Arduino Not Connected")
            self.arduino_status_label.setStyleSheet("color: red; font-size: 16px;")
            self.log_message(f"Failed to reconnect to Arduino: {e}")
            self.arm_status = False
            self.fuel_slider.setValue(0)
            self.brake_slider.setValue(0)

            self.arm_status_label.setText("DISARMED")
            self.arm_status_label.setStyleSheet("color: red; font-size: 16px;")
            self.log_message("System DISARMED")

    def send_to_arduino(self, motor_id, value):
        """
        Send a command to the Arduino server in the format 'motorID:value'.
        """
        if self.socket_connection:
            try:
                command = f"{motor_id}:{value}\n"
                self.socket_connection.sendall(command.encode())
                # self.log_message(f"Sent to Arduino: {command}")
            except Exception as e:
                self.log_message(f"Error sending command to Arduino: {e}")
        else:
            self.log_message("Socket connection to Arduino not established.")

        def check_socket_connection(self):
            try:
                self.socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket_connection.connect((self.arduino_ip, self.arduino_port))
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
                    steering_value=steering_value+self.steering_TH
                if 1500>steering_value:
                    steering_value=steering_value-self.steering_TH



                # self.log_message(f"fuel_slider: {self.fuel_slider.value()}")

                if self.fuel_slider.value()>2:
                    fuel_value = np.interp(self.fuel_slider.value(), [0, 100], [self.min_fuel, self.max_fuel])
                else:
                    fuel_value = self.min_fuel-self.fuel_offset
                # self.log_message(f"fuel_value: {fuel_value}")

                brake_value = np.interp(self.brake_slider.value(), [0, 100], [self.max_brake, self.min_brake])
                if self.gear_value_number==2:
                    gear_value = self.gear_R_arduino_value
                elif self.gear_value_number==1:
                    gear_value = self.gear_D_arduino_value
                elif self.gear_value_number==0:
                    gear_value = self.gear_N_arduino_value
                elif self.gear_value_number==3:
                    gear_value = self.gear_P_arduino_value

                arm_value = 1 if self.arm_status else 0



                vector_message = f"[{steering_value:.0f},{brake_value:.0f},{fuel_value:.0f},{gear_value:.0f},{arm_value}]\n"
                self.socket_connection.sendall(vector_message.encode())

                if (steering_value != self.previous_steering or
                        brake_value != self.previous_brake or
                        fuel_value != self.previous_fuel or
                        gear_value != self.previous_gear or
                        arm_value != self.previous_arm):
                    self.log_message(f"Sent to Arduino: {vector_message}")

                self.previous_steering = steering_value
                self.previous_brake = brake_value
                self.previous_fuel = fuel_value
                self.previous_gear = gear_value
                self.previous_arm = arm_value
            except Exception as e:
                self.log_message(f"Error sending data to Arduino: {e}")
                self.arduino_status_label.setText("Arduino Not Connected")
                self.arduino_status_label.setStyleSheet("color: red; font-size: 16px;")
        else:
            self.log_message("Socket connection to Arduino not established.")

    def set_gear(self, gear):
        """Set the current gear."""
        self.gear_value = gear
        self.gear_status_label.setText(f"Current Gear: {self.gear_value}")
        self.log_message(f"Gear changed to: {gear}")

    def update_controls(self):
        pass

    def update_config_file(self):
        # print("config updated")
        config = import_config()
        self.min_steering = int(config["min_steering"])
        self.max_steering = int(config["max_steering"])
        self.min_fuel = int(config["min_fuel"])
        self.max_fuel = int(config["max_fuel"])
        self.fuel_offset = int(config["fuel_offset"])
        self.min_brake = int(config["min_brake"])
        self.max_brake = int(config["max_brake"])
        self.gear_P_arduino_value = int(config["gear_P_arduino_value"])
        self.gear_D_arduino_value = int(config["gear_D_arduino_value"])
        self.gear_R_arduino_value = int(config["gear_R_arduino_value"])
        self.gear_N_arduino_value = int(config["gear_N_arduino_value"])
        self.gear_L_arduino_value = int(config["gear_L_arduino_value"])


        self.fuel_multiplier = float(config["fuel_multiplier"])  # Initial multiplier for fuel
        self.brake_multiplier = float(config["brake_multiplier"])  # Initial multiplier for brake
        self.steering_multiplier = float(config["fuel_multiplier"])  # Initial multiplier for brake

    def start_recording(self):
        if not self.is_recording:
            # Start recording
            try:
                # Define the codec and create VideoWriter object
                fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Codec for .avi format
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                video_filename = os.path.join(self.path_to_save_video, f"recording_{timestamp}.avi")

                # Get the size of the main window
                frame_width = self.centralWidget().width()
                frame_height = self.centralWidget().height()
                fps = 30  # Set recording FPS

                self.video_writer = cv2.VideoWriter(video_filename, fourcc, fps, (frame_width, frame_height))
                self.is_recording = True
                self.record_button.setText("Stop Recording")
                self.log_message(f"Recording started: {video_filename}")

                # Start the recording timer
                self.recording_timer.start(1000 // fps)  # Capture frames at specified FPS
            except Exception as e:
                self.log_message(f"Error starting recording: {e}")
        else:
            # Stop recording
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            self.is_recording = False
            self.record_button.setText("Start Recording")
            self.log_message("Recording stopped.")

            # Stop the recording timer
            self.recording_timer.stop()

    def capture_window_frame(self):
        try:
            # Capture the entire main window
            try:
                pixmap = self.grab()
                # Convert the pixmap to an OpenCV image
                qimage = pixmap.toImage()
                width = qimage.width()
                height = qimage.height()
                channels = 4  # Assuming RGBA
                buffer = qimage.bits().asstring(width * height * channels)
                frame = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, channels))
                frame = cv2.cvtColor(frame,
                                     cv2.COLOR_RGBA2BGR)  # Convert to BGR format for OpenCV                self.video_writer.write(frame)
            except Exception as e:
                logging.error(f"Frame capture/recording error: {e}")
                self.log_message(f"Error capturing or recording frame: {e}")


            # Write the frame to the video if recording
            if self.is_recording and self.video_writer:
                self.video_writer.write(frame)
        except Exception as e:
            self.log_message(f"Error capturing window frame: {e}")

    def closeEvent(self, event):
        """Stop video managers and close the app."""
        self.main_video_manager.stop()
        self.secondary_video_manager.stop()
        self.PTZ_controller.close()
        super().closeEvent(event)
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        if self.recording_timer.isActive():
            self.recording_timer.stop()
        if self.timer.isActive():
            self.timer.stop()
        if self.vector_timer.isActive():
            self.vector_timer.stop()
        if self.video_manager:
            self.video_manager.stop()

            self.video_manager = None
        event.accept()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RemoteDrivingApp()
    window.show()
    sys.exit(app.exec_())


    window.show()
    sys.exit(app.exec_())

