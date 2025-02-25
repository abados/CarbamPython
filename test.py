from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def send_whatsapp_message(phone_number, message):
    # Path to your WebDriver
    driver = webdriver.Chrome()
    driver.get('https://web.whatsapp.com')

    # Wait for QR code scan
    print("Scan QR code to log in.")
    time.sleep(15)  # Adjust based on how long it takes you to scan

    # Search for contact
    search_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
    search_box.click()
    search_box.send_keys(phone_number + Keys.ENTER)
    time.sleep(3)

    # Send message
    message_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="6"]')
    message_box.click()
    message_box.send_keys(message + Keys.ENTER)

    print(f"Message sent to {phone_number}")
    driver.quit()

# Usage
send_whatsapp_message("+972503900336", "Hello, this is an automated message!")
