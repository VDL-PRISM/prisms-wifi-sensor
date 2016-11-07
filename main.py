import argparse
import logging
import socket
from threading import Thread
import time

from persistent_queue import PersistentQueue
import yaml

from servers import mqtt_publisher
from sensors import dylos, sht21, lcd


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
LOGGER = logging.getLogger(__name__)

methods = {'mqtt_publisher': mqtt_publisher.run}

parser = argparse.ArgumentParser(description='Reads data from Dylos sensor')
parser.add_argument('method', choices=methods.keys(),
                    help='Type of transport to use')
parser.add_argument('-c', '--config', type=argparse.FileType('r'),
                    default=open('config.yaml'), help='Configuration file')

args = parser.parse_args()
config = config = yaml.load(args.config)

# TODO: Protect against failures here!

LOGGER.info("Loading persistent queue")
queue = PersistentQueue('dylos.queue')

LOGGER.info("Getting host name")
hostname = socket.gethostname()
LOGGER.info("Hostname: %s", hostname)

# Set up sensors
LOGGER.info("Starting LCD screen")
lcd_screen = lcd.setup()

LOGGER.info("Starting air quality sensor")
air_sensor = dylos.setup(config['serial']['port'],
                         config['serial']['baudrate'])

LOGGER.info("Starting temperature sensor")
temp_sensor = sh21.setup()

# Read data from the sensor
def read_data():
    sequence_number = 0

    while True:
        try:
            LOGGER.info("Getting new data from sensors")
            air_data = air_sensor()
            temp_data = temp_sensor()
            now = time.time()
            sequence_number += 1

            # combine data together
            data = {"sampletime": now,
                    "sequence": sequence_number,
                    "monitorname": hostname,
                    **air_data,
                    **temp_data}

            lcd_screen("S: {}  L: {}".format(air_data['small'], air_data['large']))

            # Save data for later
            queue.push(data)

        except KeyboardInterrupt:
            break
        except Exception as e:
            # Keep going no matter of the exception -- hopefully it will fix itself
            LOGGER.exception("An exception occurred!")

            LOGGER.debug("Waiting 15 seconds and then trying again")
            time.sleep(15)
            continue

t = Thread(target=read_data)
t.daemon = True
t.start()

# Start server
try:
    methods[args.method](config, hostname, queue, lcd_screen)
except KeyboardInterrupt:
    print("Qutting...")






