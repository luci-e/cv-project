from gpiozero import LED
from time import sleep

led = LED(24)
led.blink()

while(True):
    sleep(1)

