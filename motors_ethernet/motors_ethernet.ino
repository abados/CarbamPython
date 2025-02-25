#include <SoftwareSerial.h>
#include <Ethernet.h>

// Ethernet settings
byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED }; // Replace with your MAC address
IPAddress ip(192, 168, 1, 177);                      // Replace with a valid IP address for your network
EthernetServer server(80); 

      
// SoftwareSerial setup for communication with the second Arduino
SoftwareSerial secondArduino(7, 8); // RX, TX

const int numMotors = 5;
const int motorPins[numMotors] = {3, 5, 6, 9}; // Motor pins

// Global Variables
int motorValues[numMotors] = {1500, 1500, 1500, 1500,0}; // Default motor PWM values (neutral)
int fail_safe = 0; // Fail-safe state
int Permision_to_controll = 0; // Fail-safe state

unsigned long lastInputTime = 0; // Tracks the last input time
const unsigned long failSafeTimeout = 3000; // 3-second timeout in milliseconds
int desired_values[numMotors] = {1500, 1500, 1500, 1500,0}; // Desired PWM values
int kp = 10; // Proportional control constant
int min_analog_value = 200; // Minimum analog input
int max_analog_value = 500; // Maximum analog input

// Function to log messages to both Serial and second Arduino
void logMessage(const String &message) {
//  Serial.println(message);
  secondArduino.println(message);
}

// Function to send PWM to a motor
void sendPWM(int pin, int pwmValue) {
  pwmValue = constrain(pwmValue, 1000, 2000); // Ensure PWM value is within range
  digitalWrite(pin, HIGH);
  delayMicroseconds(pwmValue);               // ON duration
  digitalWrite(pin, LOW);
  delayMicroseconds(20000 - pwmValue);       // OFF duration to complete 20 ms
}

// Function to control motors
void controlMotors() {
  sendPWM(motorPins[0], desired_values[0]);
//  Serial.print(" steering: ");    
//  Serial.println(desired_values[0]);   
  for (int i = 1; i < numMotors; i++) {
    if (Permision_to_controll == 1) {
      // Simulate proportional control
      int currentValue = analogRead(A0 + i);
      

      int desiredValue = map(desired_values[i], 1000, 2000, min_analog_value, max_analog_value);
      int error = desiredValue - currentValue;
  
      int pwmValue = 1500 + (kp * error);
      if (abs(error) < 0) { // If within tolerance, stop the motor
        pwmValue = pwmValue -250;
      }
      if (abs(error) > 0) { // If within tolerance, stop the motor
        pwmValue = pwmValue +250;
      }      


      pwmValue = constrain(pwmValue, 1000, 2000); 

      if (i==1){
       //  Serial.println(message);
      Serial.print(" potensiometer: ");      
      Serial.print(currentValue);
      Serial.print(" desiredValue: ");      
      Serial.print(desiredValue);
      Serial.print(" desiredValue: ");      
      Serial.println(pwmValue);  
       
      }
      if (abs(error) < 5) { // If within tolerance, stop the motor
        pwmValue = 1500;
      }

      motorValues[i] = pwmValue;
    } else {
      motorValues[i] = 1500; // Neutral state
    }

    
    sendPWM(motorPins[i], motorValues[i]);
  }
}
void parseCommand(String command) {
    command.remove(0, 1); // Remove the starting '['
    command.remove(command.length() - 1, 1); // Remove the ending ']'

    int index = 0; // Index for tracking the parsed value
    while (command.length() > 0 && index < numMotors + 1) {
        int delimiterIndex = command.indexOf(','); // Find the next delimiter
        String value = (delimiterIndex == -1) ? command : command.substring(0, delimiterIndex); // Extract the value
        int parsedValue = value.toInt(); // Convert to integer

        if (index < numMotors) {
            desired_values[index] = parsedValue; // Update desired motor values
        } else {
            fail_safe = parsedValue; // Update fail-safe flag
        }

        command = (delimiterIndex == -1) ? "" : command.substring(delimiterIndex + 1); // Move to the next value
        index++;
    }

    lastInputTime = millis(); // Update the last input time
}

void handleSerialInput() {
    EthernetClient client = server.available(); // Check for incoming client connection
    if (client) {
//        Serial.println("New client connected");
        String command = "";

        // Read data from the client
        while (client.connected()) {
            if (client.available()) {
                char c = client.read();
                Serial.print(c); // Debug: Print received characters
                if (c == '\n') { // End of the command
                    break;
                }
                command += c;
            }
        }

        // Process the command if available
        if (command.length() > 0) {
//            Serial.println("Received: " + command);

            // Check the command format and parse it
            if (command.startsWith("[") && command.endsWith("]")) {
                parseCommand(command); // Call parseCommand to process the input
//                Serial.println("Input parsed successfully.");
            } else {
                Serial.println("Invalid input format.");
            }
        }

        client.flush(); // Clear any remaining data in the client's buffer
//        Serial.println("Keeping connection open."); // Do not stop the client here
    }
}



// Fail-safe function
void activateFailSafe() {
  fail_safe = 0;
  Permision_to_controll = 0;
  desired_values[1] = 2000;
  desired_values[2] = 1000;
  sendPWM(motorPins[1], 2000);
  sendPWM(motorPins[2], 1000);
 
  secondArduino.println("pause");   
  delay(50); 
  sendPWM(motorPins[1], 1990);
  sendPWM(motorPins[2], 1010);
  delay(100); 
  sendPWM(motorPins[1], 1980);
  sendPWM(motorPins[2], 1020);
  delay(100); 
  sendPWM(motorPins[1], 1970);
  sendPWM(motorPins[2], 1030); 
  delay(300); 
  sendPWM(motorPins[1], 1960);
  sendPWM(motorPins[2], 1040); 

  delay(500); 
  sendPWM(motorPins[1], 1950);
  sendPWM(motorPins[2], 1030); 
  delay(500); 
  sendPWM(motorPins[1], 1940);
  sendPWM(motorPins[2], 1030); 
  delay(500); 
  sendPWM(motorPins[1], 1950);
  sendPWM(motorPins[2], 1050); 
        
  secondArduino.println("continue");
     
  sendPWM(motorPins[1], 1500);
  sendPWM(motorPins[2], 1500);      
  }


// `setup()` function: Called once when the Arduino starts
void setup() {
  // Set motor pins as output
  for (int i = 0; i < numMotors; i++) {
    pinMode(motorPins[i], OUTPUT);
  }
  // Start serial communication
  Serial.begin(9600);
  secondArduino.begin(9600); // Initialize communication with the second Arduino
  logMessage("Arduino is ready.");
    // Initialize Ethernet
  Ethernet.begin(mac, ip);
  server.begin();
  Serial.println("Ethernet server is ready.");
}

// `loop()` function: Continuously executes the main logic
void loop() {
  handleSerialInput();
  controlMotors();

  

    
  // Check for fail-safe timeout
  if ((millis() - lastInputTime > failSafeTimeout)) {
    if (fail_safe == 1){
      activateFailSafe();
      desired_values[4]=0;
      secondArduino.println("Fail safe");
       }
  }
  if (desired_values[4]==0){
    if (fail_safe == 1){
      activateFailSafe();
      }
  }

  if ((desired_values[4]==1)&&(fail_safe==0)){
    if ((desired_values[2]<1700)&&(desired_values[1]>1200)){
     fail_safe = 1; 
     Permision_to_controll=1;
     secondArduino.println("Fail safe diactivatade");
    }
  }   
}
