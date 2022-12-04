int sampleRate = 50;    // Sensor reading freq (hz)
unsigned long sampleDelay = 1e6/sampleRate; //time(us) between samples
unsigned long tapDelay = 150; // time between tap checks (I found this rate to work the best)
unsigned long timeStart = 0;  // start time sample
unsigned long timeEnd = 0;    // end time sample


bool sampleSensors() {
  timeEnd = micros();
  if(timeEnd - timeStart >= sampleDelay) {
    displaySampleRate(timeEnd);
    timeStart = timeEnd;

    // Read the sensors and store their outputs in global variables
    sampleTime = millis();
    readAccelSensor();     // values stored in "ax", "ay", and "az"
    readPhotoSensor();     // value stored in "ppg"
    return true;
  }

  return false;
}

void displaySampleRate(unsigned long currentTime) {
     int nSamples = 100;
     static int count = 0;
     static unsigned long lastTime = 0;

     count++;
     if(count == nSamples) {
        double avgRate = nSamples * 1e6 / (currentTime - lastTime);
        String message = String(avgRate) + " Hz";
        writeDisplay(message.c_str(), 3, false);

        // reset
        count = 0;
        lastTime = currentTime;
    }
}
