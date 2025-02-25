import cv2
import logging

logging.basicConfig(level=logging.DEBUG)

rtsp_url = "http://192.168.1.101:8081"

try:
    # Use GStreamer for more robust handling
    capture = cv2.VideoCapture(
        f"rtspsrc location={rtsp_url} ! decodebin ! videoconvert ! appsink",
        cv2.CAP_GSTREAMER
    )

    if not capture.isOpened():
        raise Exception("Failed to open RTSP stream")

    while True:
        ret, frame = capture.read()
        if not ret:
            logging.error("Failed to read frame")
            break

        cv2.imshow("RTSP Stream", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except Exception as e:
    logging.error(f"Error with RTSP stream: {e}")

finally:
    if 'capture' in locals():
        capture.release()
    cv2.destroyAllWindows()
