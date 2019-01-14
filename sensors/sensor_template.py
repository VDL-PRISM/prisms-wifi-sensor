import logging
from threading import Thread

LOGGER = logging.getLogger(__name__)


def setup_sensor(config):
    return SensorName()


class SensorName:
    def __init__(self):
        self.running = True
        self.state = {}

    def start(self):
        self.thread = Thread(target=self._run)
        self.thread.start()

    def _sleep(self, amount):
        while amount > 0:
            if not self.running:
                break

            if amount > 1:
                time.sleep(1)
                amount -= 1
            else:
                time.sleep(amount)
                amount = 0

    def _run(self):
        while self.running:
            # Update state
            LOGGER.info("Updating state of sensor")
            self.state = {'measurement_name': 'value'}

            # Sleep
            self._sleep(60)

    def read(self):
        return self.state

    def stop(self):
        self.running = False
        self.thread.join()
