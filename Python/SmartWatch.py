from ECE16Lib.Communication import Communication
from ECE16Lib.HRMonitor import HRMonitor
from ECE16Lib.Pedometer import Pedometer
from datetime import datetime
from pyowm import OWM
from time import time

# Send weather info (location, date, time, temp) for San Diego using weather API
def send_weather(weather):
    date = "Date:" + str(datetime.now().date())                                   # Get date in given timezone
    time = "Time:" + str(datetime.now().strftime("%I:%M:%S %p"))                  # Format time as 12 hour cycle 
    temperature = "Temp:"+ str(weather.temperature('fahrenheit')['temp']) + "F"   # Format temperature string
    comms.send_message("San Diego")  # Send location name to ESP32
    comms.send_message(date)         # Send date info to ESP32
    comms.send_message(time)         # Send time info to ESP32
    comms.send_message(temperature)  # Send temperature info to ESP32

if __name__ == "__main__":
  fs = 50                         # sampling rate
  num_samples = 500               # 10 seconds of data @ 50Hz
  process_time = 1                # compute the hr every 1 second
  active_time =  5                # check for 10 sec of inactivity
  active = "idle"                 # Keep track of idle/active
  prev_steps = 0                  # Keep track of previous step count
  prev_step_time = time()         # Keep track of time of previous step
  state = 1                       # Keep track of state for FSM 

  owm = OWM('e8a392af37b228fa334688a95e08f604').weather_manager()   # Get weather API object
  weatherSD = owm.weather_at_place('San Diego,CA,US').weather       # Get weather for SD

  hr_monitor = HRMonitor(num_samples, fs)                           # Create heart rate monitoring object
  ped = Pedometer(num_samples, fs, [])                              # Create pedometer object 
  #comms = Communication("BTRV", 115200) 
  comms = Communication("/dev/cu.usbserial-027601E0", 115200)                            # Set up communication
  comms.clear()                   # just in case any junk is in the pipes

#   gmm = hr_monitor.train()        # Train GMM model, we decided not to use the ML approach
    
  print("Finished training GMM model")
  
  try:
    previous_time = time()
    while(True):
      message = comms.receive_message()
      if message != None:
        message = message.strip().replace("\n","")  # Remove endline character

      # Track state of FSM
      if(message == "weather"):
        state = 1
        continue
      elif(message == "heart"):
        state = 2
        continue
      elif(message == "steps"):
        state = 3
        continue

      # Run depending on state
      # State 1: Send weather data for San Diego
      if(state == 1):
        if time() - previous_time > 1:
            print("Sending weather data")
            send_weather(weatherSD)
            previous_time = time()
      # State 2: Act as heart rate monitor
      elif(state == 2): 
          if message != None:
            try:
              (t, hr) = message.split(',')
            except ValueError:        # if corrupted data, skip the sample
              continue
        
            # Collect data in the heart rate monitor
            t = (int(t) - int(t[0]))/1e3
            hr_monitor.add(int(t), int(hr))

            # if enough time has elapsed, process the data and plot it
            current_time = time()
            if (current_time - previous_time > process_time):
              print("Sending Heart Rate data")
              previous_time = current_time

              # Predict heart rate based on model we trained 
            #   hr_est = hr_monitor.predict(gmm)
              hr, peaks, filtered = hr_monitor.process_new()
              print(f"Heart Rate: {hr}")

              # Send heart rate to MCU
              try:
                comms.send_message(str(int(hr)))
              except:
                print("HR was NaN")
                continue
      # State 3: Act as pedometer/Idle detector
      elif(state == 3):
            if message != None:
              try:
                (m1, ax, ay, az) = message.split(',')
              except ValueError:        # if corrupted data, skip the sample
                continue

              # Collect data in the pedometer
              ped.add(int(ax),int(ay),int(az))

              # if enough time has elapsed, process the data and plot it
              current_time = time()
              if (current_time - previous_time > process_time):
                print("Sending Pedometer data")
                previous_time = current_time

                steps, peaks, filtered, jumps, peaks_j = ped.process()
                print(f"Step count: {steps}")

                # Get time of last step
                if prev_steps != steps:
                  prev_step_time = time()
                  # prev_steps = steps
                
                # Check for idle/active
                if (current_time - prev_step_time > active_time): # if 10 sec pass
                #   prev_step_time = current_time
                  if(prev_steps == steps): ## and steps are the same = idle
                    active = "idle"
                  else:
                    active = "active"
                  prev_steps = steps

                  # Send steps to MCU
                comms.send_message(str(steps))
                comms.send_message(active)

  except(Exception, KeyboardInterrupt) as e:
    print(e)                     # Exiting the program due to exception
  finally:
    print("Closing connection.")
    comms.send_message("sleep")  # stop sending data
    comms.close()


# Arduino Side  
#   array with options: [Weather, Heart rate, Pedometer/Active]
#   Button would cycle between these states and send to python a message saying which state it is
#   We would send the relevant data depending on state 
# . if(button state == 1) #WEATHER
#       1st: Send string saying "weather" to python program
#       2nd: receive location temp time from python program and display on OLED
#   if(button state == 2) HEART RATE
#       1st: Send string saying "Heart Rate" to Python program
#       2nd: Send string containing heart rate data 
#       3rd: Receive estimated heart rate and display on OLED
#   if(button state == 3) IDLE/STEPS
# .     1st: Send string saying "Steps" to Python program
#       2nd: Send string containing steps data 
#       3rd: Receive estimated steps and display on OLED

# Python Side 
# if(command = "Weather")
#    1st: Get weather for San Diego and send to MCU
#    owm = OWM('e8a392af37b228fa334688a95e08f604').weather_manager()   # Get weather API object
#    weatherSD = owm.weather_at_place('San Diego,CA,US').weather 
#    Call below function to send weather data to MCU 
#    def send_weather(ser, weather):
#       date = "Date:" + str(datetime.now().date())                                   # Get date in given timezone
#       time = "Time:" + str(datetime.now().strftime("%I:%M:%S %p"))                  # Format time as 12 hour cycle 
#       temperature = "Temp:"+ str(weather.temperature('fahrenheit')['temp']) + "F"     # Format temperature string
#       comms.send_message("San Diego")     # Send location name to ESP32
#       comms.send_message(date)         # Send date info to ESP32
#       comms.send_message(time)         # Send time info to ESP32
#       comms.send_message(temperature)  # Send temperature info to ESP32
# 
# if(command = "Heart")
#    1st: use logic from L7Ch2
# if(command = "Steps")
#    1st: Use same logic as pedometer Lab 
#
#
