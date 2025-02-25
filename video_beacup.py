import cv2
import time
import logging
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

class VideoManager(QThread):
    frame_ready = pyqtSignal(object)  # Emits the processed frame
    connection_lost = pyqtSignal()    # Emits when connection is lost
    latency_calculated = pyqtSignal(float)  # Emits latency in ms

    def __init__(self, video_url, label, reconnect_interval=5, motioneye_url=None, auth=None):
        super().__init__()
        self.video_url = video_url
        self.label = label
        self.running = True
        self.capture = None

        self.reconnect_interval = reconnect_interval  # Time in seconds to wait before reconnecting
        self.latency_video = 0
        self.high_latency_threshold = 300  # High latency in ms
        self.low_latency_threshold = 100   # Low latency in ms
        self.motioneye_url = motioneye_url  # MotionEye API URL
        self.auth = auth  # Tuple for basic auth (username, password)

    def run(self):
        while self.running:
            try:
                self._connect_stream()  # Attempt to connect to the video stream
                while self.running and self.capture.isOpened():
                    start_time = time.time()  # Timestamp when frame is received
                    ret, frame = self.capture.read()  # Read a frame from the video stream
                    if ret:
                        end_time = time.time()  # Timestamp after processing the frame
                        self.latency_video = (end_time - start_time) * 1000  # Latency in ms
                        self.latency_calculated.emit(self.latency_video)

                        # Adjust stream settings dynamically based on latency
                        self.adjust_stream_settings(self.latency_video)

                        # Overlay latency on the frame
                        frame = self.add_latency_to_frame(frame, self.latency_video)

                        self.frame_ready.emit(frame)  # Emit the processed frame
                    else:
                        logging.warning("Frame not retrieved. Retrying...")  # Frame not retrieved
                        self._handle_disconnection()
                        break
            except Exception as e:
                logging.error(f"Error in video stream: {e}")  # Log any exceptions
                self._handle_disconnection()

    def _connect_stream(self):
        # Attempt to open the video stream
        logging.info(f"Attempting to connect to video stream at {self.video_url}")
        self.capture = cv2.VideoCapture(self.video_url)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.capture.isOpened():
            raise ConnectionError(f"Failed to open video stream at {self.video_url}")
        else:
            logging.info("Video stream connected successfully")

    def _handle_disconnection(self):
        # Handle disconnection from the video stream
        if self.capture:
            logging.warning("Releasing video capture due to disconnection")
            self.capture.release()
        self.connection_lost.emit()
        logging.info(f"Reconnecting in {self.reconnect_interval} seconds...")
        time.sleep(self.reconnect_interval)  # Wait before attempting to reconnect

    def stop(self):
        # Stop the video manager thread
        self.running = False
        if self.capture and self.capture.isOpened():
            logging.info("Releasing video capture")
            self.capture.release()

    def add_latency_to_frame(self, frame, latency):
        try:
            # Convert latency to string and overlay it on the frame
            latency_text = f"Latency: {latency:.2f} ms"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1
            font_color = (0, 255, 0)  # Green text
            thickness = 2
            org = (10, 30)  # Top-left corner of text
            frame = cv2.putText(frame, latency_text, org, font, font_scale, font_color, thickness, cv2.LINE_AA)
        except Exception as e:
            logging.error(f"Error adding latency to frame: {e}")
        return frame

    def adjust_stream_settings(self, latency):
        # Adjust the stream settings dynamically based on latency thresholds
        if not self.motioneye_url:
            logging.warning("MotionEye URL not provided. Skipping dynamic adjustments.")
            return

        if latency > self.high_latency_threshold:
            logging.info("High latency detected. Lowering frame rate and resolution.")
            self.update_motioneye_settings(framerate=10, resolution=(640, 480))  # Lower frame rate and resolution
        elif latency < self.low_latency_threshold:
            logging.info("Low latency detected. Increasing frame rate and resolution.")
            self.update_motioneye_settings(framerate=30, resolution=(1280, 720))  # Higher frame rate and resolution

    def update_motioneye_settings(self, framerate, resolution):
        # Update MotionEye settings using its API
        if not self.motioneye_url or not self.auth:
            logging.warning("MotionEye URL or authentication not provided. Cannot update settings.")
            return

        data = {
            "framerate": framerate,
            "width": resolution[0],
            "height": resolution[1]
        }

        try:
            response = requests.post(self.motioneye_url, json=data, auth=self.auth)
            if response.status_code == 200:
                logging.info("MotionEye settings updated successfully")
            else:
                logging.warning(f"Failed to update settings: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Error updating MotionEye settings: {e}")

    def display_frame(self, frame):
        try:
            # Convert the frame to RGB and resize to fit the label
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized_frame = cv2.resize(frame, (self.label.width(), self.label.height()))
            height, width, channel = resized_frame.shape
            qimg = QImage(resized_frame.data, width, height, channel * width, QImage.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(qimg))
        except Exception as e:
            logging.error(f"Error displaying frame: {e}")
