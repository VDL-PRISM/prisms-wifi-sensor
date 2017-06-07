import logging
import subprocess
import time

DHT22_PIN   = 'P8_11'
PM_PORT      = '/dev/ttyO1'
LOGGER = logging.getLogger(__name__)
REQUIREMENTS = ['https://github.com/adafruit/Adafruit_Python_DHT/archive/master.zip#Adafruit-DHT==1.3.2',
                'Adafruit-BBIO==0.0.30',
                'pyserial==3.1.1']


def setup_sensor(config):
    return AirStation()


class AirStation:
    def __init__(self):
        import Adafruit_BBIO.UART as UART
        import serial

        self.type = 'output'
        self.name = 'airu'

        # Turn off LEDs
        subprocess.call('echo none > /sys/class/leds/beaglebone\:green\:usr0/trigger', shell=True)
        subprocess.call('echo none > /sys/class/leds/beaglebone\:green\:usr1/trigger', shell=True)
        subprocess.call('echo none > /sys/class/leds/beaglebone\:green\:usr2/trigger', shell=True)
        subprocess.call('echo none > /sys/class/leds/beaglebone\:green\:usr3/trigger', shell=True)

        UART.setup("UART1")

        # Open a connection with the PMS3003 sensor
        self._pm = serial.Serial(port=PM_PORT,
                                 baudrate=9600,
                                 rtscts=True,
                                 dsrdtr=True)

        if not self._pm.isOpen():
            self._pm.open()

    def get_pm(self):
        """
        Gets the current particular matter reading as a concentration per unit volume as reported by
        the Shinyei PPD42NJ sensor.

        For more information on how this reading is obtained, please see the
        official datasheet from Seeed Studio:

        http://www.seeedstudio.com/wiki/images/4/4c/Grove_-_Dust_sensor.pdf

        :return: A float representing the concentration of particles per unit volume.
        :raises: exception.RetryException if no reading was obtained in the retry period.
        """

        # Flush the existing input buffer to ensure a fresh reading
        self._pm.flushInput()
        res = self._pm.read(24)

        # Add up each of the bytes in the frame
        sum = 0
        for i in range(0, 22):
            sum = sum + res[i]

        # Calculate the checksum using the last two bytes of the frame
        chksum = 256*res[22] + res[23]

        if sum != chksum:
            return None

        # Get the PM readings using the TSI standard
        pm1_upperb = res[4]
        pm1_lowerb = res[5]
        pm1 = 256*pm1_upperb + pm1_lowerb

        pm25_upperb = res[6]
        pm25_lowerb = res[7]
        pm25 = 256*pm25_upperb + pm25_lowerb

        pm10_upperb = res[8]
        pm10_lowerb = res[9]
        pm10 = 256*pm10_upperb + pm10_lowerb

        # Get the PM readings using the atmosphere as the standard
        pm1at_upperb = res[10]
        pm1at_lowerb = res[11]
        pm1at = 256*pm1at_upperb + pm1at_lowerb

        pm25at_upperb = res[12]
        pm25at_lowerb = res[13]
        pm25at = 256*pm25at_upperb + pm25at_lowerb

        pm10at_upperb = res[14]
        pm10at_lowerb = res[15]
        pm10at = 256*pm10at_upperb + pm10at_lowerb

        # Return the TSI standard readings
        return (pm1, pm25, pm10)

    def start(self):
        pass

    def read(self):
        import Adafruit_DHT

        humidity, temperature = Adafruit_DHT.read(Adafruit_DHT.DHT22, DHT22_PIN)
        humidity = round(humidity, 2) if humidity is not None else None
        temperature = round(temperature, 2) if temperature is not None else None

        pm1, pm25, pm10 = self.get_pm()

        data = {'humidity': (humidity, '%'),
                'temperature': (temperature, '°C'),
                'pm1': (pm1, 'ug/m3'),
                'pm25': (pm25, 'ug/m3'),
                'pm10': (pm10, 'ug/m3')}


        LOGGER.debug("Data from AirU: %s", data)
        return data

    def stop(self):
        self._pm.close()
