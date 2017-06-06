import logging
from subprocess import run, check_output, CalledProcessError, TimeoutExpired
import re
import threading
import time


LOGGER = logging.getLogger(__name__)

def setup_sensor(config):
    return WirelessMonitor()


class WirelessMonitor:
    def __init__(self):
        self.type = 'output'
        self.name = 'wireless'

        self.connecting = threading.Event()

    def start(self):
        # Figure out what the wireless interface is
        try:
            self.interface = check_output('iwconfig 2> /dev/null '
                                          '| grep -o "^[[:alnum:]]\+"',
                                          shell=True)
            self.interface = self.interface.strip().decode('utf8')
            LOGGER.debug("Monitoring wireless interface {}".format(self.interface))
        except Exception:
            LOGGER.warning("No wireless interface to monitor!")
            self.interface = None

    def stop(self):
        pass

    def read(self):
        data = {}

        if self.interface is None:
            return data

        data['ip_address'] = (self.ip_address(), 'ip_address')

        try:
            # Get stats
            with open('/proc/net/wireless') as f:
                lines = [line for line in f if line.strip().startswith(self.interface)]
            stats = lines[0].split()
            stats = stats[2:11]
            stats[0] = float(stats[0])
            stats = [int(x) for x in stats]

            data.update({'link_quality': (stats[0], 'num'),
                         'signal_level': (stats[1], 'dBm'),
                         'noise_level': (stats[2], 'dBm'),
                         'rx_invalid_nwid': (stats[3], 'num'),
                         'rx_invalid_crypt': (stats[4], 'num'),
                         'rx_invalid_frag': (stats[5], 'num'),
                         'tx_retires': (stats[6], 'num'),
                         'invalid_misc': (stats[7], 'num'),
                         'missed_beacon': (stats[8], 'num')})
        except Exception:
            LOGGER.exception("Exception occurred while getting wireless stats")

        try:
            result = check_output('iwconfig {}'.format(self.interface),
                                  shell=True,
                                  timeout=5)
            result = result.decode('utf8')

            # Determine if connected
            data['associated'] = (int('Not-Associated' not in result), 'associated')

            # Get bit rate
            m = re.search("Bit Rate=(\\d+) Mb/s", result)
            if m is not None:
                data['data_rate'] = (int(m.group(1)), 'Mbps')

            # If not associated, start thread to try to connect
            if not data['associated'][0]:
                LOGGER.warning("Not associated! Trying to reconnect")

                if not self.connecting.is_set():
                    LOGGER.info("Starting thread to connect")
                    t = threading.Thread(target=self.connect)
                    t.start()
                else:
                    LOGGER.info("A thread is already trying to connect to WiFi")

        except Exception:
            LOGGER.exception("Exception occurred while running iwconfig")

        return data

    def ip_address(self):
        if self.interface is None:
            return ''

        try:
            ip = check_output('ifconfig {} '
                              '| grep "inet addr"'
                              '| cut -d: -f2 '
                              '| cut -d" " -f1'.format(self.interface),
                              shell=True,
                              timeout=5)
            ip = ip.strip().decode('utf8')
            LOGGER.info("IP address: %s", ip)
            return ip
        except Exception:
            LOGGER.warning("Unable to get IP address")
            return ''

    def connect(self):
        self.connecting.set()

        try:
            LOGGER.info("Turning off wireless interface")
            run("ifdown {}".format(self.interface), shell=True)
            LOGGER.info("Done turning off wireless interface")
        except Exception:
            LOGGER.exception("Exception while turning off WiFi")

        LOGGER.info("Waiting before starting wireless interface")
        time.sleep(10)

        try:
            LOGGER.info("Turning on wireless interface")
            run("ifup {}".format(self.interface), shell=True)
            LOGGER.info("Done turning on wireless interface")
        except Exception:
            LOGGER.exception("Exception while turning on WiFi")

        self.connecting.clear()

