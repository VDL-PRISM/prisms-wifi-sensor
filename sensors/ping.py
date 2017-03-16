import logging
import subprocess
from subprocess import run, check_output, CalledProcessError, TimeoutExpired
from threading import Thread, Lock
import time

import utils.pingparse as pingparse

LOGGER = logging.getLogger(__name__)


class PingMonitor:
    def __init__(self, destination, interval=10):
        self.interval = interval
        self.destination = destination

        self.errors = 0
        self.loss = 0
        self.latency = []
        self.total = 0

        self.lock = Lock()
        self.running = True

        self.sensor_thread = Thread(target=self._run)
        self.sensor_thread.start()

    def _run(self):
        while self.running:
            # Run a ping
            start = time.time()
            result = run('ping -c 1 -w 5 {}'.format(self.destination),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True,
                         timeout=10)

            with self.lock:
                self._parse(result)

            end = time.time()

            sleep_time = self.interval - (end - start)
            time.sleep(sleep_time)

    def _parse(self, result):
        if result.returncode == 0:
            result = pingparse.parse(result.stdout.decode('utf8'))
            self.latency.append(float(result['avgping']))

            if int(result['packet_loss']) != 0:
                self.loss += 1
        else:
            self.errors += 1

        self.total += 1

    def stats(self):
        with self.lock:
            latency = sum(self.latency) / len(self.latency) if len(self.latency) > 0 else 0

            data = {'ping_errors': self.errors,
                    'ping_latency': latency,
                    'ping_packet_loss': self.loss,
                    'ping_total': self.total}

            self.errors = 0
            self.loss = 0
            self.latency = []
            self.total = 0

        return data

    def stop(self):
        self.running = False
