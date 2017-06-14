from datetime import datetime
import logging
import os
import threading
import time


LOGGER = logging.getLogger(__name__)


def setup_sensor(config):
    return LCDWriter(display_aq=config['display_air_quality'])


# pylint: disable=too-many-instance-attributes
class LCDWriter:
    def __init__(self, display_aq=False):
        self.type = 'input'
        self.name = 'fake_lcd'
        self.display_aq = display_aq

        self.lock = threading.Lock()

        self.line1 = ""
        self.line2 = ""

        self.pm1 = 0
        self.pm25 = 0
        self.pm10 = 0
        self.update_air_time = None

        self.queue_size = 0
        self.update_queue_time = None

        self.address = ""


    def start(self):
        pass

    def stop(self):
        pass

    def status(self, message):
        self.display(line1=message)

    def data(self, data):
        self.update_air_time = datetime.now()
        self.queue_size = data['queue_length'][0]

        self.pm1 = data.get('pm1', [0])[0]
        self.pm25 = data.get('pm25', [0])[0]
        self.pm10 = data.get('pm10', [0])[0]
        self.address = data.get('ip_address', [''])[0].split('.')[-1]

        self.display_data()

    def transmitted_data(self, queue_length):
        self.update_queue_time = datetime.now()
        self.queue_size = queue_length
        self.display_data()

    def display_data(self):
        update_air_time = "" if self.update_air_time is None else \
                          self.update_air_time.strftime("%H:%M")
        update_queue_time = "" if self.update_queue_time is None else \
                            self.update_queue_time.strftime("%H:%M")

        if self.display_aq:
            part_1 = 'bad' if self.pm1 is None else self.pm1
            part_2 = 'bad' if self.pm25 is None else self.pm25
            part_3 = 'bad' if self.pm10 is None else self.pm10
        else:
            valid_data = 'not ok' if self.pm1 is None or self.pm25 is None or self.pm10 is None else 'ok'
            part_1 = ''
            part_2 = ''
            part_3 = valid_data

        line1 = "{: >3} {: >3} {: >3} {}".format(part_1,
                                                 part_2,
                                                 part_3,
                                                 update_air_time)
        line2 = "{: >4} {: >5} {}".format(self.address,
                                          self.queue_size,
                                          update_queue_time)

        self.display(line1=line1, line2=line2)

    def display(self, line1=None, line2=None):
        with self.lock:
            if line1 is not None:
                self.line1 = line1

            if line2 is not None:
                self.line2 = line2

            LOGGER.debug("Line 1: %s", self.line1)
            LOGGER.debug("Line 2: %s", self.line2)
