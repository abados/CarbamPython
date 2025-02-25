import cv2

def stream_video(url):
    cap = cv2.VideoCapture(url)

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        cv2.imshow('Video Stream', frame)

        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # url = 'http://192.168.150.193:81/stream' # rihgt click on the camera feed and copy the image address
    url = 'http://192.168.1.71:8081'
    stream_video(url)
