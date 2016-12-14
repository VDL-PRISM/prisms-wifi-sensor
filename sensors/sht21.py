import logging

LOGGER = logging.getLogger(__name__)


def get_temp():
    with open('/sys/bus/i2c/drivers/sht21/1-0040/temp1_input') as file_:
        temp = file_.readline().strip()

    return float(temp) / 1000


def get_humidity():
    with open('/sys/bus/i2c/drivers/sht21/1-0040/humidity1_input') as file_:
        humidity = file_.readline().strip()

    return float(humidity) / 1000


def setup():
    try:
        get_temp()
        sht_present = True
    except Exception as exp:
        LOGGER.warning("Exception %s: Probably means there is no sht sensor"
                       " available", exp)
        sht_present = False

    def read():
        if not sht_present:
            return {"temperature": None, "humidity": None}

        try:
            LOGGER.debug("Reading from sht sensor")
            return {"temperature": round(get_temp()),
                    "humidity": round(get_humidity())}
        except Exception as exp:
            LOGGER.error("Error while reading from sht: %s", exp)
            return {"temperature": None, "humidity": None}

    return read
