import logging

import Adafruit_BBIO.UART as UART
from driver.sht_driver import sht21
from driver.lcd_driver_adafruit import lcd_driver
import serial

LOGGER = logging.getLogger(__name__)

def setup_air_quality(port, baudrate):
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
        small, large = [int(x) for x in line.split(b',')]
        LOGGER.debug("Read from serial port: %s %s", small, large)
        return {"small": small, "large": large}

    return read


def setup_temp_sensor():
    try:
        sht = sht21()
        sht.get_temp()
    except IOError:
        LOGGER.debug("No sht sensor available")
        sht = None

    def read():
        if sht is None:
            return {"temperature": None, "humidity": None}

        LOGGER.debug("Reading from sht sensor")
        return {"temperature": round(sht.get_temp()),
                "humidity": round(sht.get_humidity())}

    return read


def setup_lcd_sensor():
    lcd = lcd_driver()
    lcd.setup()

    line1_ = ''
    line2_ = ''

    def write(line1=None, line2=None):
        nonlocal line1_
        nonlocal line2_

        LOGGER.debug("Writing to lcd screen")

        if line1 is not None:
            line1_ = line1

        if line2 is not None:
            line2_ = line2

        LOGGER.debug("Line 1: %s", line1_)
        LOGGER.debug("Line 2: %s", line2_)

        lcd.lcdcommand('00000001')  # Reset
        lcd.lcdprint(line1_)
        lcd.lcdcommand('11000000')  # Move cursor down
        lcd.lcdprint(line2_)
        lcd.lcdcommand('10000000')  # Move cursor to beginning

    return write
