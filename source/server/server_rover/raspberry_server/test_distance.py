from gpiozero import DistanceSensor
from time import sleep

sensor = DistanceSensor(echo=18, trigger=23)
while True:
    print('Distance: ', sensor.distance * 100)
    sleep(0.5)