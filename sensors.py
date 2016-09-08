# import Adafruit_BBIO.UART as UART
# from driver.sht_driver import sht21

def setup_air_quality(port, baudrate):
    # Setup UART
    UART.setup("UART1")

    ser = serial.Serial(port=port, baudrate=baudrate,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS)
    ser.open()

    def read():
        line = ser.readline()
        small, large = [int(x) for x in line.split(',')]
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
