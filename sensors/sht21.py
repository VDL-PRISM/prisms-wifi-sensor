import logging

LOGGER = logging.getLogger(__name__)


def setup_sensor(config):
    return Sht21()


class Sht21:
    def __init__(self):
        self.type = 'output'
        self.name = 'sht21'

    def _get_temp(self):
        with open('/sys/bus/i2c/drivers/sht21/1-0040/temp1_input') as f:
            temp = f.readline().strip()
            return float(temp) / 1000

    def _get_humidity(self):
        with open('/sys/bus/i2c/drivers/sht21/1-0040/humidity1_input') as f:
            humidity = f.readline().strip()
            return float(humidity) / 1000

    def start(self):
        pass

    def read(self):
        try:
            temp = round(self._get_temp() * 1.8 + 32, 2)
        except Exception:
            temp = None

        try:
            humidity = round(self._get_humidity(), 2)
        except Exception:
            humidity = None

        return {'temperature': (temp, '°F'), 'humidity': (humidity, '%')}

    def stop(self):
        pass
