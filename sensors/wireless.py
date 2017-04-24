import logging
from subprocess import run, check_output, CalledProcessError, TimeoutExpired
import re
import threading
import time


LOGGER = logging.getLogger(__name__)
HEADER = ['associated', 'data_rate', 'link_quality', 'signal_level',
          'noise_level', 'rx_invalid_nwid', 'rx_invalid_crypt',
          'rx_invalid_frag', 'tx_retires', 'invalid_misc', 'missed_beacon']


class WirelessMonitor:
    def __init__(self):
        self.connecting = threading.Event()

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

    def stats(self):
        if self.interface is None:
            return dict(zip(HEADER, [False, -256, -256, 0, 0, 0, 0, 0]))

        try:
            # Get stats
            with open('/proc/net/wireless') as f:
                lines = [line for line in f if line.strip().startswith(self.interface)]
            stats = lines[0].split()
            stats = stats[2:-1]
            stats[0] = float(stats[0])
            stats = [int(x) for x in stats]
        except Exception:
            LOGGER.exception("Exception occurred while getting wireless stats")
            stats = [False, -256, -256, 0, 0, 0, 0, 0]

        try:
            result = check_output('iwconfig {}'.format(self.interface),
                                  shell=True)
            result = result.decode('utf8')

            # Determine if connected
            if 'Not-Associated' in result:
                associated = 0
            else:
                associated = 1

            # Get bit rate
            m = re.search("Bit Rate=(\\d+) Mb/s", result)
            if m is not None:
                data_rate = int(m.group(1))
            else:
                data_rate = 0

            # If not associated, start thread to try to connect
            if not associated:
                LOGGER.warning("Not associated! Trying to reconnect")

                if not self.connecting.is_set():
                    LOGGER.info("Starting thread to connect")
                    t = threading.Thread(target=self.connect)
                    t.start()
                else:
                    LOGGER.info("A thread is already trying to connect to WiFi")

        except Exception:
            LOGGER.exception("Exception occurred while running iwconfig")
            associated = 0
            data_rate = 0

        return dict(zip(HEADER, [associated, data_rate] + stats))

    def ip_address(self):
        if self.interface is None:
            return ''

        try:
            ip = check_output('ifconfig {} '
                              '| grep "inet addr"'
                              '| cut -d: -f2 '
                              '| cut -d" " -f1'.format(self.interface),
                              shell=True)
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
        time.sleep(10)

        try:
            LOGGER.info("Turning on wireless interface")
            run("ifup {}".format(self.interface), shell=True)
            LOGGER.info("Done turning on wireless interface")
        except Exception:
            LOGGER.exception("Exception while turning on WiFi")

        self.connecting.clear()

