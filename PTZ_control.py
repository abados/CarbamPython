import sys
import logging
from onvif import ONVIFCamera
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QComboBox
from config import import_config
import json
import threading

import time




# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class PTZCameraController:
    def __init__(self, host, port, username, password):
        try:
            self.camera = ONVIFCamera(host, port, username, password)
            self.media_service = self.camera.create_media_service()
            self.ptz_service = self.camera.create_ptz_service()
            self.profile = self.media_service.GetProfiles()[0]
            self.ptz_token = self.profile.token
            config = import_config()
            Locations = json.loads(config["Camera_Locations"])  # Convert JSON string to dictionary
            self.Location_1 = Locations.get("Location_1", {"pan": 0.0, "tilt": 0.0, "zoom": 0.0})
            self.Location_2 = Locations.get("Location_2", {"pan": 0.0, "tilt": 0.0, "zoom": 0.0})
            self.Location_3 = Locations.get("Location_3", {"pan": 0.0, "tilt": 0.0, "zoom": 0.0})

            logging.info("Camera initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize the camera: {e}")


    def get_ptz_status(self):
        try:
            status = self.ptz_service.GetStatus({'ProfileToken': self.ptz_token})
            logging.info(f"PTZ status retrieved: {status}")
            return status
        except Exception as e:
            logging.error(f"Failed to retrieve PTZ status: {e}")
            return None

    def wait_until_idle(self, interval=0.5):
        """Waits until the camera stops all movements."""
        logging.info("Waiting for the camera to become idle...")
        while True:
            status = self.get_ptz_status()
            if status:
                if status.MoveStatus.PanTilt != 'MOVING' and status.MoveStatus.Zoom != 'MOVING':
                    logging.info("Camera is now idle.")
                    break
            time.sleep(interval)

    def absolute_move(self, pan, tilt, zoom=0.0, pan_speed=6.0, tilt_speed=6.0):
        try:
            request = self.ptz_service.create_type("AbsoluteMove")
            request.ProfileToken = self.ptz_token
            request.Position = {
                "PanTilt": {"x": pan, "y": tilt},
                "Zoom": {"x": zoom},
            }
            request.Speed = {
                "PanTilt": {"x": pan_speed, "y": tilt_speed},
                "Zoom": {"x": 1.0},
            }
            self.ptz_service.AbsoluteMove(request)
            logging.info(f"Absolute move: pan={pan}, tilt={tilt}, zoom={zoom}")
        except Exception as e:
            logging.error(f"Failed to execute absolute move: {e}")

    def relative_move(self, pan, tilt, zoom=0.0, pan_speed=6.0, tilt_speed=6.0):
        try:
            request = self.ptz_service.create_type("RelativeMove")
            request.ProfileToken = self.ptz_token
            request.Translation = {
                "PanTilt": {"x": pan, "y": tilt},
                "Zoom": {"x": zoom},
            }
            request.Speed = {
                "PanTilt": {"x": pan_speed, "y": tilt_speed},
                "Zoom": {"x": 1.0},
            }
            self.ptz_service.RelativeMove(request)
            logging.info(f"Relative move: pan={pan}, tilt={tilt}, zoom={zoom}")
        except Exception as e:
            logging.error(f"Failed to execute relative move: {e}")

    def stop(self):
        try:
            request = self.ptz_service.create_type("Stop")
            request.ProfileToken = self.ptz_token
            request.PanTilt = True
            request.Zoom = True
            self.ptz_service.Stop(request)
            logging.info("PTZ movement stopped.")
        except Exception as e:
            logging.error(f"Failed to stop PTZ movement: {e}")

    def go_to_location(self, location):
        """Moves the camera to a predefined location asynchronously."""
        def move_to_location():
            locations = {
                1: self.Location_1,  # Example values for Location_1
                2: self.Location_2,  # Example values for Location_2
                3: self.Location_3,  # Example values for Location_3
                4: {"pan": 0.0, "tilt": -0.5, "zoom": 0.0}   # Example values for Location_4
            }

            if location in locations:
                if location in [1, 2]:
                    # Go through Location_3 first
                    logging.info(f"Moving through Location_3 before reaching Location_{location}")
                    coords_3 = locations[3]
                    self.absolute_move(coords_3["pan"], coords_3["tilt"], coords_3["zoom"])
                    logging.info("Waiting at Location_3 for 3 seconds...")
                    time.sleep(5)

                # Move to the final destination
                coords = locations[location]
                logging.info(f"Moving to Location_{location}")
                self.absolute_move(coords["pan"], coords["tilt"], coords["zoom"])
            else:
                logging.error(f"Invalid location: {location}")

        # Start the movement in a separate thread
        threading.Thread(target=move_to_location, daemon=True).start()
    def close(self):
        """Cleanup resources and prepare for shutdown."""
        try:
            # Stop any ongoing PTZ movement
            self.stop()
            logging.info("Camera PTZ movements stopped.")
        except Exception as e:
            logging.error(f"Error stopping PTZ movements during shutdown: {e}")

        try:
            # Explicitly close the camera session
            if self.camera:
                self.camera.devicemgmt.__transport.close()  # Close transport layer
                self.camera = None
            logging.info("Camera connection closed successfully.")
        except Exception as e:
            logging.error(f"Error closing camera connection: {e}")
class CameraControlApp(QMainWindow):
    def __init__(self, ptz_controller):
        super().__init__()
        self.ptz_controller = ptz_controller
        self.selected_location = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PTZ Camera Control")
        self.setGeometry(100, 100, 400, 300)

        # Create buttons
        self.up_button = QPushButton("↑")
        self.up_button.setFixedSize(50, 50)
        self.up_button.clicked.connect(lambda: self.ptz_controller.relative_move(0.0, 0.1))

        self.down_button = QPushButton("↓")
        self.down_button.setFixedSize(50, 50)
        self.down_button.clicked.connect(lambda: self.ptz_controller.relative_move(0.0, -0.1))

        self.left_button = QPushButton("←")
        self.left_button.setFixedSize(50, 50)
        self.left_button.clicked.connect(lambda: self.ptz_controller.relative_move(-0.1, 0.0))

        self.right_button = QPushButton("→")
        self.right_button.setFixedSize(50, 50)
        self.right_button.clicked.connect(lambda: self.ptz_controller.relative_move(0.1, 0.0))

        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self.move_to_selected_location)

        # Location selection dropdown
        self.location_selector = QComboBox()
        self.location_selector.addItems([f"Location {i}" for i in range(1, 11)])
        self.location_selector.currentIndexChanged.connect(self.update_selected_location)

        # Layout
        layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.left_button)
        button_layout.addWidget(self.up_button)
        button_layout.addWidget(self.right_button)
        button_layout.addWidget(self.down_button)

        layout.addLayout(button_layout)
        layout.addWidget(self.location_selector)
        layout.addWidget(self.go_button)

        # Set central widget
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def update_selected_location(self, index):
        self.selected_location = index + 1  # Locations are 1-based
        logging.info(f"Selected location: {self.selected_location}")

    def move_to_selected_location(self):
        if self.selected_location:
            self.ptz_controller.go_to_location(self.selected_location)
        else:
            logging.error("No location selected.")


if __name__ == "__main__":
    # Replace with your camera's IP, port, username, and password
    camera = PTZCameraController("192.168.1.64", 80, "OnvifUser", "a1s2d3f4")

    app = QApplication(sys.argv)
    window = CameraControlApp(camera)
    window.show()
    sys.exit(app.exec_())
