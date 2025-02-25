import av
import time
import logging
import numpy as np
from hikvisionapi import Client
from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap
import cv2

logging.basicConfig(level=logging.DEBUG)

CAMERA_IP = '192.168.1.64'
USERNAME = 'admin'
PASSWORD = 'a1s2d3f4'

class VideoManager(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    connection_lost = pyqtSignal()
    audio_ready = pyqtSignal(bytes)  # Signal to emit audio data


    def __init__(self, video_url, label, hikvision_ip=CAMERA_IP, username=USERNAME, password=PASSWORD, reconnect_interval=5):
        super().__init__()
        self.rtsp_url = video_url
        self.label = label
        self.running = True
        self.container = None
        self.reconnect_interval = reconnect_interval
        self.hikvision_client = None
        frame_ready = pyqtSignal(np.ndarray)
        audio_ready = pyqtSignal(bytes)  # Signal to emit audio data
        connection_lost = pyqtSignal()

        try:
            # Initialize Hikvision client
            self.hikvision_client = Client(f"http://{hikvision_ip}", username, password)
        except Exception as e:
            logging.error(f"Failed to initialize Hikvision client: {e}")
            self.hikvision_client = None

    def run(self):
        while self.running:
            try:
                self._connect_stream()
                for packet in self.container.demux(video=0):
                    if not self.running:
                        break
                    for frame in packet.decode():
                        if not self.running:
                            break
                        try:
                            img = frame.to_ndarray(format="bgr24")
                            self.frame_ready.emit(img)
                        except Exception as e:
                            logging.error(f"Error decoding frame: {e}")
                    time.sleep(1 / 50)
            except Exception as e:
                logging.error(f"Unexpected error in video stream: {e}")
                self._handle_disconnection()

    def _connect_stream(self):
        try:
            self.container = av.open(self.rtsp_url)
            logging.info(f"Connected to RTSP stream at {self.rtsp_url}")
        except Exception as e:
            logging.error(f"Failed to open RTSP stream at {self.rtsp_url}: {e}")
            raise ConnectionError(f"Failed to open RTSP stream at {self.rtsp_url}: {e}")

    def _handle_disconnection(self):
        try:
            if self.container:
                self.container.close()
            self.container = None
        except Exception as e:
            logging.error(f"Error closing stream container: {e}")

        self.connection_lost.emit()
        logging.info(f"Disconnected. Attempting to reconnect in {self.reconnect_interval} seconds...")

        # Retry connecting to the stream
        time.sleep(self.reconnect_interval)
        if self.running:
            self.run()  # Reattempt streaming

    def stop(self):
        logging.debug("Stopping video stream...")
        self.running = False
        try:
            if self.container:
                self.container.close()
            self.container = None
        except Exception as e:
            logging.error(f"Error stopping video stream: {e}")
        cv2.destroyAllWindows()
        logging.debug("Video stream stopped.")

    def display_frame(self, frame):
        try:
            # Convert BGR (OpenCV default) to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized_frame = cv2.resize(frame, (self.label.width(), self.label.height()))
            height, width, channel = resized_frame.shape
            qimg = QImage(resized_frame.data, width, height, channel * width, QImage.Format_RGB888)

            # Use a thread-safe mechanism to update GUI
            self.label.setPixmap(QPixmap.fromImage(qimg))
        except cv2.error as e:
            logging.error(f"OpenCV error while displaying frame: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while displaying frame: {e}")

    def ptz_control(self, action, speed=1):
        commands = {
            'UP': 'UP',
            'DOWN': 'DOWN',
            'LEFT': 'LEFT',
            'RIGHT': 'RIGHT',
            'ZOOM_IN': 'ZOOM_IN',
            'ZOOM_OUT': 'ZOOM_OUT',
            'STOP': ''
        }

        if action not in commands:
            logging.error(f"Invalid PTZ action: {action}")
            return

        payload = {
            'action': 'start' if action != 'STOP' else 'stop',
            'code': commands[action],
            'arg1': speed,
            'arg2': 0,
            'arg3': 0
        }

        if not self.hikvision_client:
            logging.error("Hikvision client is not initialized. PTZ command cannot be sent.")
            return

        try:
            response = self.hikvision_client.ptz.ctrl(payload)
            if response.status_code == 200:
                logging.info(f"PTZ command '{action}' sent successfully.")
            else:
                logging.error(f"Failed to send PTZ command '{action}': {response.text}")
        except Exception as e:
            logging.error(f"Error sending PTZ command '{action}': {e}")
