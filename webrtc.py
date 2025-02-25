from playwright.sync_api import sync_playwright
arduino_ip=carbam-arduino.adizag.bond

def stream_webrtc():
    url = "https://carbam-cam.adizag.bond/webrtcstreamer.html?video=videocap%3A%2F%2F0&options=rtptransport%3Dtcp%26timeout%3D60&"

    with sync_playwright() as p:
        # Launch browser in visible (non-headless) mode
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)

        print("Streaming WebRTC. Leave the browser open to maintain the connection.")
        input("Press Enter to stop...")

        browser.close()

stream_webrtc()
