import cv2
import numpy as np
import time

def calculate_velocity_with_ai(camera_index, model_cfg, model_weights, class_file, frame_rate, pixel_to_meter_ratio, target_class="person"):
    """
    Calculate velocity of an object from a live camera feed using AI-based object detection.

    :param camera_index: Index of the camera to use.
    :param model_cfg: Path to the YOLO configuration file.
    :param model_weights: Path to the YOLO weights file.
    :param class_file: Path to the class labels file.
    :param frame_rate: Frame rate of the video stream (frames per second).
    :param pixel_to_meter_ratio: Conversion factor from pixels to meters.
    :param target_class: Object class to track (default is "person").
    """
    # Load YOLO model
    net = cv2.dnn.readNet(model_weights, model_cfg)
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]

    # Load class labels
    with open(class_file, "r") as f:
        classes = [line.strip() for line in f.readlines()]

    # Open the camera
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise ValueError(f"Unable to open camera with index {camera_index}.")

    prev_position = None
    time_interval = 1 / frame_rate

    print("Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Prepare the frame for YOLO
        height, width, _ = frame.shape
        blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416), swapRB=True, crop=False)
        net.setInput(blob)
        outputs = net.forward(output_layers)

        # Process detections
        detected_position = None
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5 and classes[class_id] == target_class:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    detected_position = (center_x, center_y)
                    break
            if detected_position:
                break

        if detected_position:
            # Track velocity if previous position exists
            if prev_position is not None:
                displacement_x = (detected_position[0] - prev_position[0]) * pixel_to_meter_ratio
                displacement_y = (detected_position[1] - prev_position[1]) * pixel_to_meter_ratio

                velocity_x_mps = displacement_x / time_interval
                velocity_y_mps = displacement_y / time_interval

                velocity_x_kmh = velocity_x_mps * 3.6
                velocity_y_kmh = velocity_y_mps * 3.6

                # Overlay velocity on the video
                text = f"Vx: {velocity_x_kmh:.2f} km/h, Vy: {velocity_y_kmh:.2f} km/h"
                cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                print(f"Velocity -> X: {velocity_x_kmh:.2f} km/h, Y: {velocity_y_kmh:.2f} km/h")

            prev_position = detected_position

            # Draw detected object on the frame
            cv2.circle(frame, detected_position, 5, (0, 0, 255), -1)

        # Display the live feed
        cv2.imshow("Live Velocity Tracking (AI)", frame)

        # Exit loop with 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


# Parameters
camera_index = 0  # First available camera
model_cfg = "yolov3.cfg"  # Path to YOLO configuration file
model_weights = "yolov3.weights"  # Path to YOLO pre-trained weights file
class_file = "coco.names"  # Path to class labels file
frame_rate = 30  # Camera frame rate
pixel_to_meter_ratio = 0.01  # Conversion factor (calibrate as needed)
target_class = "person"  # Class to track

# Run velocity calculation
calculate_velocity_with_ai(camera_index, model_cfg, model_weights, class_file, frame_rate, pixel_to_meter_ratio, target_class)
