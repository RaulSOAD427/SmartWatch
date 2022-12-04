/*
 * Global variables
 */
const int BUTTON_PIN = 21;        // GPIO Pin for push button
int ax = 0; int ay = 0; int az = 0; // Acceleration (from readAccelSensor())

int ppg = 0;        // PPG from readPhotoSensor() (in Photodetector tab)
int sampleTime = 0; // Time of last sample (in Sampling tab)
int previous = 0;
int interface = 0;
int line    = 0;  // Track which line to write on 
bool sending;
 
String state[3] = {"weather","heart","steps"};  // Which interface to use

/*
 * Initialize the various components of the wearable
 */
void setup() {
  setupAccelSensor();
  setupCommunication();
  setupDisplay();
  setupPhotoSensor();
  setupMotor();
  pinMode(BUTTON_PIN,INPUT);
  sending = false;
  writeDisplay("Sleep", 0, true);
  sendMessage(state[interface]);
}

/*
 * The main processing loop
 */
void loop() {
  // Check for button press
  end = millis();

  // Clear display and update which interface to show
  if(checkButton()){
    clearDisplay();
    sendMessage(state[interface]);
  } 

  // Receive weather data
  if(state[interface] == "weather"){
    for (int i = 0; i < 4; ++i){
        String message = receiveMessage();
        if (message != "") {
            writeDisplay(message.c_str(), line, false);
            line++;
            // Only four rows in OLED
            if (line > 3) {
                line = 0;
            }
        }
    }
  }

  // Receive Heart rate data
  else if(state[interface] == "heart"){
    String message = receiveMessage();
    if(message == "" && previous < 1){
      message = "0";
    }
    if(message != ""){
      previous = int(message.c_str());
      String hr = "Heart Rate: " + message;
      writeDisplay(hr.c_str(),0,true);
    }
  }

  // Receive Pedometer/Idle Detector data 
  else if(state[interface] == "steps"){
    // Receive number of steps
    String message = receiveMessage();
    if(message == "" && previous < 1){
      message = "0";
    }
    if(message != "0"){
      previous = int(message.c_str());
      String steps = "Steps: " + message;
      writeDisplay(steps.c_str(),0,true);
    }
    // Receive idle/active
    message = receiveMessage();
    // Activate/deactivate motor for idle/active
    if(message != ""){  
      writeDisplay(message.c_str(),1,false);
      if(message == "idle"){
        activateMotor(500);
      }else if(message == "active" || message == ""){
        deactivateMotor();
      }
    }
  }

  // Send appropriate data if in heart rate or pedometer modes
  if(sampleSensors()) {
    if(state[interface] == "heart"){
        String hr = String(sampleTime) + "," + String(ppg) ;
        sendMessage(hr);

    }else if(state[interface] == "steps"){
        String st = String(sampleTime) + "," + String(ax) + "," + String(ay) + "," + String(az);
        sendMessage(st);   
    }
  }

}

// Check if the button has been pressed, change location being used and clear previous screen if so 
bool checkButton(){
  if (end - start > 200 && digitalRead(BUTTON_PIN) == LOW) {
    interface++;
    start = end;
    if (interface > 2) {   
      interface = 0;
    }
    return true;
   }
   
  return false;
}

    // if(message == "idle")
    // print idle
    // else if(message == "active")
    // print ("active")

// # Arduino Side  
// #   array with options: [Weather, Heart rate, Pedometer/Active]
// #   Button would cycle between these states and send to python a message saying which state it is
// #   We would send the relevant data depending on state 
// # . if(button state == 1) #WEATHER
// #       1st: Send string saying "weather" to python program
// #       2nd: receive location temp time from python program and display on OLED
// #   if(button state == 2) HEART RATE
// #       1st: Send string saying "Heart Rate" to Python program
// #       2nd: Send string containing heart rate data 
// #       3rd: Receive estimated heart rate and display on OLED
// #   if(button state == 3) IDLE/STEPS
// # .     1st: Send string saying "Steps" to Python program
// #       2nd: Send string containing steps data 
// #       3rd: Receive estimated steps and display on OLED
