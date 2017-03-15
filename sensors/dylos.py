import logging

import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.UART as UART
import serial

DYLOS_POWER_PIN = "P8_10"
TIMEOUT = 5
LOGGER = logging.getLogger(__name__)

class Dylos:
    def __init__(self, port='/dev/ttyO1', baudrate=9600, timeout=TIMEOUT):
        self.running = True

        # Setup UART
        UART.setup("UART1")

        self.ser = serial.Serial(port=port,
                                 baudrate=baudrate,
                                 parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE,
                                 bytesize=serial.EIGHTBITS,
                                 timeout=timeout)

        if not self.ser.isOpen():
            self.ser.open()

    def read(self):
        retries = 0

        # Keep reading from serial port until we get some data
        while True:
            line = self.ser.readline()

            if not self.running:
                raise Exception("Stop reading from serial port")

            if line != b'':
                break

            if retries > (60 / TIMEOUT) + 2:
                LOGGER.debug("Dylos must be off, so turning it on")
                # Dylos must be off, so turn it on
                GPIO.setup(DYLOS_POWER_PIN, GPIO.OUT)
                GPIO.output(DYLOS_POWER_PIN, GPIO.LOW)
                retries = 0

            retries += 1

        LOGGER.debug("Read from serial port: %s", line)
        small, large = [int(x.strip()) for x in line.split(b',')]
        LOGGER.debug("Small: %s, Large: %s", small, large)
        return {"small": small, "large": large}

    def stop(self):
        self.running = False
        self.ser.close()
