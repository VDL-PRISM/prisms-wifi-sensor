from collections import namedtuple
import logging
from subprocess import run, check_output, CalledProcessError, TimeoutExpired



LOGGER = logging.getLogger(__name__)
HEADER = ['connected', 'link_quality', 'signal_level', 'noise_level',
          'rx_invalid_nwid', 'rx_invalid_crypt', 'rx_invalid_frag',
          'tx_retires', 'invalid_misc', 'missed_beacon']


class WirelessMonitor:
    def __init__(self):
        # Figure out what the wireless interface is
        try:
            self.interface = check_output('iwconfig 2> /dev/null '
                                          '| grep -o "^[[:alnum:]]\+"',
                                          shell=True)
            self.interface = self.interface.strip().decode('utf8')
            LOGGER.debug("Monitoring wireless interface {}".format(self.interface))
        except CalledProcessError:
            LOGGER.warning("No wireless interface to monitor!")
            self.interface = None

    def stats(self):
        if self.interface is None:
            return dict(zip(HEADER, [False, -256, -256, 0, 0, 0, 0, 0]))

        # Get stats
        with open('/proc/net/wireless') as f:
            lines = [line for line in f if line.strip().startswith(self.interface)]
        stats = lines[0].split()
        stats = stats[2:-1]
        stats[0] = float(stats[0])
        stats = [int(x) for x in stats]

        # Determine if connected
        try:
            result = check_output('iwconfig {}'.format(self.interface),
                                  shell=True)
            result = result.decode('utf8')

            if 'Not-Associated' in result:
                connected = False
            else:
                connected = True
        except CalledProcessError:
            connected = False

        return dict(zip(HEADER, [connected] + stats))

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
        except CalledProcessError:
            LOGGER.warning("Unable to get IP address")
            return ''
