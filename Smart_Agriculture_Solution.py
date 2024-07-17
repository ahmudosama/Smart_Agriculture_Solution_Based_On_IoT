import sys
sys.path.append('/home/raspberrypi/.local/lib/python3.9/site-packages')

import Adafruit_DHT
import BlynkLib
import RPi.GPIO as GPIO
import busio
import digitalio
import board
from adafruit_mcp3xxx.mcp3008 import MCP3008
from adafruit_mcp3xxx.analog_in import AnalogIn
from time import sleep

# Set GPIO mode (BCM mode is recommended)
GPIO.setmode(GPIO.BCM)

# Blynk authentication token
BLYNK_AUTH = '5ldncdb1dC9aM5n5WKQxapR9k6PJZwMm'

# Initialize Blynk
blynk = BlynkLib.Blynk(BLYNK_AUTH)

# DHT11 setup
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4

# LDR setup
LDR_PIN = 16

# PIR motion sensor setup
PIR_PIN = 18
BUZZER_PIN = 27

# Analog sensor setup using MCP3008
SPI_CLK = board.SCK
SPI_MISO = board.MISO
SPI_MOSI = board.MOSI
SPI_CS = digitalio.DigitalInOut(board.D5)  # Using board.D5 for CS

spi = busio.SPI(SPI_CLK, MOSI=SPI_MOSI, MISO=SPI_MISO)
mcp = MCP3008(spi, SPI_CS)

rain_sensor = AnalogIn(mcp, 0)  # Connect rain sensor to CH0
soil_sensor = AnalogIn(mcp, 1)  # Connect soil moisture sensor to CH1

# Pump control setup
PUMP_PIN = 22
GPIO.setup(PUMP_PIN, GPIO.OUT)
GPIO.output(PUMP_PIN, GPIO.LOW)

# Function to read DHT11 sensor and update Blynk
def read_dht11():
    humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
    if humidity is not None and temperature is not None:
        print(f"Temp={temperature:.1f}C Humidity={humidity:.1f}%")
        try:
            blynk.virtual_write(0, temperature)
            blynk.virtual_write(1, humidity)
        except Exception as e:
            print(f"Error writing to Blynk: {e}")
    else:
        print("Failed to retrieve data from humidity sensor")

# Function to check LDR sensor and update Blynk
def check_ldr_and_update_blynk():
    ldr_status = GPIO.input(LDR_PIN)
    print(f"LDR Status: {ldr_status}")
    if ldr_status == GPIO.LOW:
        print("Light detected!")
        try:
            blynk.virtual_write(6, 255)
        except Exception as e:
            print(f"Error writing to Blynk: {e}")
    else:
        print("No light detected.")
        try:
            blynk.virtual_write(6, 0)
        except Exception as e:
            print(f"Error writing to Blynk: {e}")

# Function for PIR motion detection callback
def motion_detection(channel):
    if GPIO.input(PIR_PIN):
        print("Motion detected!")
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        try:
            blynk.virtual_write(5, 1)
        except Exception as e:
            print(f"Error writing to Blynk: {e}")
    else:
        print("No motion detected.")
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        try:
            blynk.virtual_write(5, 0)
        except Exception as e:
            print(f"Error writing to Blynk: {e}")

# Function to scale the raw sensor values
def scale_value(raw_value, raw_min, raw_max, scaled_min, scaled_max):
    return (raw_value - raw_min) * (scaled_max - scaled_min) / (raw_max - raw_min) + scaled_min

# Function to check rain sensor and update Blynk
def check_rain_sensor_and_update_blynk():
    rain_value = rain_sensor.value
    rain_ml = scale_value(rain_value, 0, 65535, 0, 40)  # Map to 0-40 ml
    print(f"Rain Sensor Value: {rain_value}, Mapped Value: {rain_ml} ml")
    try:
        blynk.virtual_write(3, rain_ml)
    except Exception as e:
        print(f"Error writing to Blynk: {e}")

# Function to check soil moisture sensor and update Blynk
def check_soil_moisture_and_update_blynk():
    moisture_value = soil_sensor.value
    moisture_percent = scale_value(moisture_value, 0, 65535, 0, 100)  # Map to 0-100%
    print(f"Soil Moisture Value: {moisture_value}, Mapped Value: {moisture_percent}%")
    try:
        blynk.virtual_write(2, moisture_percent)
    except Exception as e:
        print(f"Error writing to Blynk: {e}")

# Blynk handler for controlling the pump
@blynk.on("V4")
def v1_write_handler(value):
    try:
        if int(value[0]) == 1:
            GPIO.output(PUMP_PIN, GPIO.HIGH)
        else:
            GPIO.output(PUMP_PIN, GPIO.LOW)
    except Exception as e:
        print(f"Error handling pump control: {e}")

# Setup GPIO and event detection for motion sensor
GPIO.setup(LDR_PIN, GPIO.IN)
GPIO.setup(PIR_PIN, GPIO.IN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.output(BUZZER_PIN, GPIO.LOW)
GPIO.add_event_detect(PIR_PIN, GPIO.BOTH, callback=motion_detection, bouncetime=300)

try:
    while True:
        read_dht11()
        check_ldr_and_update_blynk()
        check_rain_sensor_and_update_blynk()
        check_soil_moisture_and_update_blynk()
        try:
            blynk.run()
        except Exception as e:
            print(f"Error running Blynk: {e}")
        sleep(2)

except KeyboardInterrupt:
    print("Exiting...")
finally:
    GPIO.cleanup()
