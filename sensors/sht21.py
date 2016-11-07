import logging

LOGGER = logging.getLogger(__name__)


class sht21:
    def get_temp(self):
        with open('/sys/bus/i2c/drivers/sht21/1-0040/temp1_input') as f:
            temp = f.readline().strip()

        return float(temp) / 1000

    def get_humidity(self):
        with open('/sys/bus/i2c/drivers/sht21/1-0040/humidity1_input') as f:
            humidity = f.readline().strip()

        return float(humidity) / 1000


def setup():
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
