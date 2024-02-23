import machine
import time
import urequests
import network
import ntptime
import ujson

# Set the timezone offset for Eastern Time (ET), UTC-5
TIMEZONE_OFFSET = -4 * 3600

# Initialize the DHT22 sensor
pir_pin = machine.Pin(15, machine.Pin.IN)

# Initialize the Pin LED sensor
led = machine.Pin(18, machine.Pin.OUT)

# Servo configuration
servo_pin = machine.PWM(machine.Pin(4), freq=50)
servo_pin2 = machine.PWM(machine.Pin(32), freq=50)
servo_min = 40
servo_max = 115

# State variable to track servo position and motion state
servo_position = 0.0
motion_state = 0
servo_position2 = 0.0
motion_state2 = 0

def set_servo_position(position):
    # Map the position (0-1) to the servo's duty cycle range
    duty_cycle = int(servo_min + (servo_max - servo_min) * position)
    servo_pin.duty(duty_cycle)

def set_servo_position2(position):
    # Map the position (0-1) to the servo's duty cycle range
    duty_cycle = int(servo_min + (servo_max - servo_min) * position)
    servo_pin2.duty(duty_cycle)

# Define your Wi-Fi credentials
wifi_ssid = 'Wokwi-GUEST'
wifi_password = ''

# Connect to Wi-Fi
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(wifi_ssid, wifi_password)

# Wait for Wi-Fi connection
while not wifi.isconnected():
    pass

# Firebase Realtime Database URL and secret
firebase_url = "https://bugwatch-team24-default-rtdb.firebaseio.com/"
firebase_secret = 'MqATaoiBBFB9YZCL2l9CLjkGLjEfKYdd7QEV3hqy'

# Synchronize time with an NTP server
ntptime.settime()

def read_pir_sensor():
    return pir_pin.value()

# Function to run the second servo motor
def run_motion_state2(timer):
    global motion_state2
    if motion_state2 == 0:
        set_servo_position2(1)  # Move the second servo
        motion_state2 = 1
    else:
        set_servo_position2(0.0)  # Revert the second servo
        motion_state2 = 0

# Initialize the motion_state2 variable at the global scope
motion_state2 = 0

def format_timestamp(timestamp):
    timestamp += TIMEZONE_OFFSET
    year, month, day, hour, minute, second, _, _ = time.localtime(timestamp)
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(year, month, day, hour, minute, second)

def upload_to_firebase(data):
    try:
        headers = {"Content-Type": "application/json"}
        if data == 1:
            current_time = format_timestamp(time.time())
            image_link = "https://cdn.britannica.com/23/7623-050-B434B02E/cockroach.jpg"
            data = {"date": current_time, "motion": data, "image_link": image_link}
            url = f'{firebase_url}/motion-data.json?auth={firebase_secret}'
            response = urequests.post(url, json=data)
            if response.status_code == 200:
                pass
            else:
                print(f"Failed to send data to Firebase. Status code: {response.status_code}")
            response.close()
    except Exception as e:
        print("Failed to upload data to Firebase:", e)

# Function to fetch the oil change period from Firebase
def get_oil_change_period():
    try:
        url = f'{firebase_url}/oil-period.json?auth={firebase_secret}'
        response = urequests.get(url)
        if response.status_code == 200:
            try:
                data = ujson.loads(response.text)
                if isinstance(data, int):
                    return data
                elif isinstance(data, dict) and "oil-period" in data:
                    return data["oil-period"]
            except ValueError:
                print("Invalid JSON response from Firebase.")
        else:
            print(f"Failed to fetch oil change period. Status code: {response.status_code}")
    except Exception as e:
        print("Failed to fetch oil change period:", e)

# Function to set the oil change timer based on the fetched period
def set_oil_change_timer(period):
    if period is not None:
        run_motion_state2(None)  # Start the motion immediately
        motion_state2_timer = machine.Timer(1)
        motion_state2_timer.init(period=period * 1000, mode=machine.Timer.PERIODIC, callback=run_motion_state2)

# Initial setup: Fetch the period and set the timer for the second servo
initial_oil_change_period = get_oil_change_period()
set_oil_change_timer(initial_oil_change_period)


# https://console.firebase.google.com/u/0/project/bugwatch-team24/database/bugwatch-team24-default-rtdb/data/~2F?pli=1
while True:
    pir_data = read_pir_sensor()
    if pir_data == 1:
        led.on()
        if motion_state == 0:
            set_servo_position(0.5)
            motion_state = 1
            time.sleep(5)
        led.off()
        set_servo_position(0.0)
        motion_state = 0
    upload_to_firebase(pir_data)

    # Fetch the oil change period from Firebase periodically and set the timer for the second servo
    oil_change_period = get_oil_change_period()
    if oil_change_period is not None:
        set_oil_change_timer(oil_change_period)
    time.sleep(2)
