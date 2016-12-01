import logging

import Adafruit_BBIO.UART as UART
import serial

LOGGER = logging.getLogger(__name__)


def setup(port, baudrate):
    # Setup UART
    UART.setup("UART1")

    ser = serial.Serial(port=port, baudrate=baudrate,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS)

    if not ser.isOpen():
        ser.open()

    def read():
        line = ser.readline()
        LOGGER.debug("Read from serial port: %s", line)
        small, large = [int(x.strip()) for x in line.split(b',')]
        LOGGER.debug("Small: %s, Large: %s", small, large)
        return {"small": small, "large": large}

    return read
