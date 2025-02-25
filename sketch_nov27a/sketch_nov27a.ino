void setup() {
  Serial.begin(9600); // Start serial communication
  Serial.println("Second Arduino is ready to receive!");
}

void loop() {
  if (Serial.available()) {
    String received = Serial.readStringUntil('\n'); // Read incoming data
//    Serial.print("Received from first Arduino: ");
    Serial.println(received); // Print the received data
  }
}
