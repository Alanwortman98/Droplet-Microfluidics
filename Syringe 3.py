import time
import serial
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN)
GPIO.setup(35, GPIO.OUT)

ser = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, bytesize=8, timeout=.5,
                    stopbits=serial.STOPBITS_ONE)

ser.reset_input_buffer()

print(ser.name)

input = GPIO.input(17)
             
while True:
        if GPIO.input(17):
            ser.write("start\r".encode())
            data = ser.readline()
            print(data)
            print("Aspirating")
            time.sleep(0)
            
        if not GPIO.input(17):
            ser.write("pause\r".encode())
            data = ser.readline()
            print(data)
            print("Waiting")
            time.sleep(0)

Break ()
ser.close() 
