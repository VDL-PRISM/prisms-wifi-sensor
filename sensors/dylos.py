import logging
from threading import Thread, Lock

import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.UART as UART
import serial

DYLOS_POWER_PIN = "P8_10"
TIMEOUT = 5
LOGGER = logging.getLogger(__name__)


def setup_sensor(config):
    return Dylos()


class Dylos:
    def __init__(self, port='/dev/ttyO1', baudrate=9600, timeout=TIMEOUT):
        self.type = 'output'
        self.name = 'dylos'

        self.running = True
        self.lock = Lock()

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

    def start(self):
        self.thread = Thread(target=self._run)
        self.thread.start()

    def _run(self):
        last_data = time.time()

        # Keep reading from serial port until we get some data
        while self.running:
            line = self.ser.readline()

            if not self.running:
                break

            if line == b'':
                if retries > (60 / TIMEOUT) + 2:
                    # Dylos produces a data point every 60 seconds so something
                    # must be wrong. Try starting the Dylos fan.
                    LOGGER.debug("Dylos must be off, so turning it on")
                    GPIO.setup(DYLOS_POWER_PIN, GPIO.OUT)
                    GPIO.output(DYLOS_POWER_PIN, GPIO.LOW)
                    retries = 0
            else:
                LOGGER.debug("Read from serial port: %s", line)
                small, large = [int(x.strip()) for x in line.split(b',')]
                LOGGER.debug("Small: %s, Large: %s", small, large)

                with self.lock:
                    self.small = small
                    self.large = large

                retries = 0

            retries += 1

        self.ser.close()

    def read(self):
        with self.lock:
            return {"small": self.small, "large": self.large}

    def stop(self):
        self.running = False
        self.thread.join()
