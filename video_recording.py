import os
import time
import cv2
import numpy as np
import mss
import pyaudio
import wave
import moviepy.editor as mp
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton


class ScreenAudioRecorder(QWidget):
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.video_writer = None
        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(self.capture_window_frame)
        self.path_to_save_video = "path/to/save"  # Set your save path

        self.record_button = QPushButton("Start Recording", self)
        self.record_button.clicked.connect(self.start_recording)

        layout = QVBoxLayout(self)
        layout.addWidget(self.record_button)
        self.setLayout(layout)

        self.audio_stream = None
        self.audio_filename = None
        self.frames = []

        # For audio-video merging in real time
        self.audio_frames = []
        self.video_frames = []
        self.audio_started = False
        self.video_started = False

    def start_recording(self):
        if not self.is_recording:
            # Start recording screen and audio
            try:
                # Setup for video recording
                fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Codec for .avi format
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                video_filename = os.path.join(self.path_to_save_video, f"recording_{timestamp}.avi")

                frame_width = self.centralWidget().width()
                frame_height = self.centralWidget().height()
                fps = 30  # Set FPS for recording

                self.video_writer = cv2.VideoWriter(video_filename, fourcc, fps, (frame_width, frame_height))
                self.is_recording = True
                self.record_button.setText("Stop Recording")
                self.log_message(f"Recording started: {video_filename}")

                # Setup for audio recording
                self.audio_filename = os.path.join(self.path_to_save_video, f"audio_{timestamp}.wav")
                self.start_audio_recording()

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
            self.stop_audio_recording()

            # Stop the recording timer
            self.recording_timer.stop()

            # After stopping, merge audio and video in real-time
            self.merge_audio_video()

    def capture_window_frame(self):
        try:
            # Capture the screen using mss
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # Capture the first monitor
                screen = np.array(sct.grab(monitor))  # Capture the screen
                frame = cv2.cvtColor(screen, cv2.COLOR_RGBA2BGR)  # Convert RGBA to BGR

                # Save the video frames
                if self.is_recording and self.video_writer:
                    self.video_writer.write(frame)
                    self.video_frames.append(frame)  # Add frame to video frames list
        except Exception as e:
            self.log_message(f"Error capturing screen frame: {e}")

    def start_audio_recording(self):
        try:
            self.p = pyaudio.PyAudio()

            # Set up audio stream (16-bit, mono, 44100 Hz)
            self.audio_stream = self.p.open(format=pyaudio.paInt16,
                                            channels=1,
                                            rate=44100,
                                            input=True,
                                            frames_per_buffer=1024)
            self.frames = []
            self.audio_started = True
            self.log_message("Audio recording started.")

            # Start capturing audio frames in real time
            while self.is_recording:
                data = self.audio_stream.read(1024)
                self.frames.append(data)  # Add audio frame to list
                self.audio_frames.append(data)
        except Exception as e:
            self.log_message(f"Error starting audio recording: {e}")

    def stop_audio_recording(self):
        try:
            if self.audio_stream:
                frames = self.frames

                # Save the audio to a .wav file
                with wave.open(self.audio_filename, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(44100)
                    wf.writeframes(b''.join(frames))

                self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.p.terminate()
                self.log_message(f"Audio saved to {self.audio_filename}")
        except Exception as e:
            self.log_message(f"Error stopping audio recording: {e}")

    def merge_audio_video(self):
        try:
            # Load video using moviepy
            video_clip = mp.VideoFileClip(
                os.path.join(self.path_to_save_video, f"recording_{time.strftime('%Y%m%d-%H%M%S')}.avi"))

            # Create audio clip from the saved audio file
            audio_clip = mp.AudioFileClip(self.audio_filename)

            # Set audio for video clip
            video_with_audio = video_clip.set_audio(audio_clip)

            # Write the final merged video
            output_filename = os.path.join(self.path_to_save_video, f"final_video_{time.strftime('%Y%m%d-%H%M%S')}.mp4")
            video_with_audio.write_videofile(output_filename, codec="libx264", audio_codec="aac")
            self.log_message(f"Merged audio and video saved to {output_filename}")
        except Exception as e:
            self.log_message(f"Error merging audio and video: {e}")

    def log_message(self, message):
        print(message)
