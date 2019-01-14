import logging
import subprocess
from subprocess import run, check_output, CalledProcessError, TimeoutExpired
from threading import Thread, Lock
import time

import utils.pingparse as pingparse

LOGGER = logging.getLogger(__name__)


def setup_sensor(config):
    return PingMonitor(config['name'], config['host'], config['interval'], config['prefix'])

class PingMonitor:
    def __init__(self, name, destination, interval=10, prefix=''):
        self.name = name
        self.type = 'output'

        self.destination = destination
        self.interval = interval
        self.prefix = prefix

        self.errors = 0
        self.loss = 0
        self.latency = []
        self.total = 0

        self.lock = Lock()
        self.running = True

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
            # Run a ping
            start = time.time()

            try:
                result = run('ping -c 1 -w 5 {}'.format(self.destination),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True,
                             timeout=10)
                with self.lock:
                    self._parse(result)

            except TimeoutExpired:
                LOGGER.error("Ping command timed out")
            except Exception:
                LOGGER.exception("Exception occurred while pinging")

            end = time.time()
            sleep_time = self.interval - (end - start)

            if sleep_time > 0:
                # LOGGER.debug("Sleeping for %s", sleep_time)
                self._sleep(sleep_time)
            else:
                LOGGER.warning("Sleep time is negative (%s). Ignoring...",
                               sleep_time)

    def _parse(self, result):
        if result.returncode == 0:
            result = pingparse.parse(result.stdout.decode('utf8'))
            self.latency.append(float(result['avgping']))

            if int(result['packet_loss']) != 0:
                self.loss += 1
        else:
            LOGGER.warning("Ping error: %s", result.stderr.decode('utf8'))
            self.errors += 1

        self.total += 1

    def start(self):
        self.sensor_thread = Thread(target=self._run)
        self.sensor_thread.start()

    def read(self):
        with self.lock:
            latency = sum(self.latency) / len(self.latency) if len(self.latency) > 0 else 0

            data = {self.prefix + 'ping_errors': self.errors,
                    self.prefix + 'ping_latency': latency,
                    self.prefix + 'ping_packet_loss': self.loss,
                    self.prefix + 'ping_total': self.total}

            self.errors = 0
            self.loss = 0
            self.latency = []
            self.total = 0

        return data

    def stop(self):
        self.running = False
        self.sensor_thread.join()
