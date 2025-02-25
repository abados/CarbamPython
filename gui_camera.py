from hikvisionapi import Client
import av
import cv2
import time

# Configure camera credentials and IP
CAMERA_IP = '192.168.0.64'
USERNAME = 'admin'
PASSWORD = 'a1s2d3f4'

# Initialize Hikvision API client
client = Client(f'http://{CAMERA_IP}', USERNAME, PASSWORD)


# PTZ Control Functions
# PTZ Control Function
# PTZ Control Function
# PTZ Control Function
def ptz_control(action, speed=1):
    """
    Sends PTZ control commands to the camera.

    :param action: PTZ action (e.g., 'UP', 'DOWN', 'LEFT', 'RIGHT', 'ZOOM_IN', 'ZOOM_OUT', 'STOP').
    :param speed: PTZ speed (1-7).
    """
    # Define the PTZ commands mapping
    commands = {
        'UP': 'UP',
        'DOWN': 'DOWN',
        'LEFT': 'LEFT',
        'RIGHT': 'RIGHT',
        'ZOOM_IN': 'ZOOM_IN',
        'ZOOM_OUT': 'ZOOM_OUT',
        'STOP': ''  # Stop command does not require a direction
    }

    if action not in commands:
        print(f"Invalid PTZ action: {action}")
        return

    # Build the PTZ payload
    payload = f"""
    <PTZData>
        <pan>{'start' if action != 'STOP' else 'stop'}</pan>
        <tilt>{'start' if action != 'STOP' else 'stop'}</tilt>
        <zoom>{'start' if action != 'STOP' else 'stop'}</zoom>
        <arg1>{speed}</arg1>
    </PTZData>
    """

    try:
        # Send the PTZ command to the appropriate endpoint
        response = client.call('PUT', '/ISAPI/PTZCtrl/channels/1/continuous', data=payload)
        if response.status_code == 200:
            print(f"PTZ command '{action}' sent successfully.")
        else:
            print(f"Failed to send PTZ command '{action}': {response.text}")
    except Exception as e:
        print(f"Error sending PTZ command '{action}': {e}")


# Video Stream Processing
def process_video_stream(rtsp_url):
    """
    Access and process the camera's RTSP stream using av and OpenCV.

    :param rtsp_url: RTSP URL for the video stream.
    """
    container = av.open(rtsp_url)

    for frame in container.decode(video=0):
        # Convert frame to a format compatible with OpenCV
        img = frame.to_ndarray(format='bgr24')

        # Display the video frame
        cv2.imshow('PTZ Camera Stream', img)

        # Handle keypress for exiting
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
    container.close()


if __name__ == "__main__":
    try:
        # RTSP URL
        RTSP_URL = f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}/Streaming/Channels/101"

        # Example PTZ Control
        print("Moving camera UP...")
        ptz_control('UP', speed=2)
        time.sleep(2)
        print("Stopping camera movement...")
        ptz_control('STOP')

        # Process the video stream
        print("Opening video stream...")
        process_video_stream(RTSP_URL)

    except Exception as e:
        print(f"Error: {e}")
