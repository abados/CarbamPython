import cv2
import time
import av
import logging
from hikvisionapi import Client
import numpy as np
from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap
import logging

logging.basicConfig(level=logging.DEBUG)

class VideoManager(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    connection_lost = pyqtSignal()

    def __init__(self, video_url, label, reconnect_interval=5):
        """
        Initializes the VideoManager class with the provided RTSP URL and QLabel for display.

        Args:
        - rtsp_url (str): The URL of the RTSP stream (e.g., "rtsp://192.168.1.111/camera1.sdp")
        - label (QLabel): A QLabel to display the video frames.
        - reconnect_interval (int): The interval time in seconds before reconnecting after disconnection.
        """
        super().__init__()
        self.rtsp_url = video_url
        self.label = label
        self.running = True
        self.capture = None
        self.reconnect_interval = reconnect_interval  # Time in seconds to wait before reconnecting
        self.latency_video_1 = 0
        self.latency_video_2 = 0

    def run(self):
        """
        Handles the video stream and processes frames.
        """
        frame_delay = 1 / 30  # Target frame delay for 30 FPS
        while self.running:
            try:
                self._connect_stream()
                while self.running and self.capture.isOpened():
                    start_time = time.time()  # Record start time for frame timing
                    ret, frame = self.capture.read()
                    if not self.running:  # Exit loop if stopped
                        break
                    if ret:
                        self.frame_ready.emit(frame)
                        elapsed_time = time.time() - start_time
                        remaining_time = frame_delay - elapsed_time
                        if remaining_time > 0:
                            time.sleep(remaining_time)
                    else:
                        self._handle_disconnection()
                        break
            except Exception as e:
                logging.error(f"Error in video stream: {e}")
                self._handle_disconnection()

    def _connect_stream(self):
        """
        Connects to the RTSP stream using OpenCV's VideoCapture.
        Raises a ConnectionError if the stream cannot be opened.
        """
        self.capture = cv2.VideoCapture(self.rtsp_url)
        if not self.capture.isOpened():
            raise ConnectionError(f"Failed to open RTSP stream at {self.rtsp_url}")

    def _handle_disconnection(self):
        """
        Handles stream disconnection by releasing the capture object and emitting a signal.
        Then attempts to reconnect after the specified interval.
        """
        if self.capture:
            self.capture.release()
        self.connection_lost.emit()
        time.sleep(self.reconnect_interval)  # Wait before attempting to reconnect

    def stop(self):
        """
        Stops the video stream and releases the capture object.
        """
        logging.debug("Stopping video stream...")
        self.running = False
        time.sleep(0.1)  # Allow FFmpeg to finalize any pending tasks
        if self.capture:
            if self.capture.isOpened():
                logging.debug("Releasing VideoCapture...")
                self.capture.release()
            self.capture = None
        cv2.destroyAllWindows()
        logging.debug("Video stream stopped.")

    def display_frame(self, frame):
        """
        Converts the captured frame to RGB and resizes it to fit the QLabel. Then sets it to be displayed.

        Args:
        - frame (np.ndarray): The frame captured from the video stream.
        """
        try:
            # Convert BGR (OpenCV default) to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Resize the frame to fit the label size
            resized_frame = cv2.resize(frame, (self.label.width(), self.label.height()))
            height, width, channel = resized_frame.shape
            qimg = QImage(resized_frame.data, width, height, channel * width, QImage.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(qimg))
        except Exception as e:
            logging.error(f"Error displaying frame: {e}")
