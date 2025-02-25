from hikvisionapi import Client

# Camera configuration
host = "http://192.168.0.64"  # Replace with your camera's IP address
username = "admin"  # Replace with your camera's username
password = "a1s2d3f4"  # Replace with your camera's password

# Initialize Hikvision API Client
client = Client(host, username, password)


# Test PTZ Commands
def test_ptz():
    try:
        # Pan Right
        print("Panning right...")
        client.PTZCtrl.channels[1].continuousMove(method='put', data={
            "PTZData": {
                "pan": 0.5,  # Pan speed (positive: right, negative: left)
                "tilt": 0.0,  # Tilt speed (positive: up, negative: down)
                "zoom": 0.0  # Zoom speed (positive: zoom in, negative: zoom out)
            }
        })

        # Wait for 2 seconds
        import time
        time.sleep(2)

        # Stop PTZ Movement
        print("Stopping PTZ...")
        client.PTZCtrl.channels[1].stop(method='put', data={
            "PTZData": {
                "pan": True,
                "tilt": True,
                "zoom": True
            }
        })

        print("PTZ test complete!")
    except Exception as e:
        print(f"Failed to control PTZ: {e}")


# Run the test
test_ptz()
