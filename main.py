from __future__ import print_function, division
import argparse
from datetime import datetime
import logging
import socket
from threading import Thread
import time

import msgpack
from persistent_queue import PersistentQueue
import yaml

from servers import mqtt_publisher, coap_server
from sensors import dylos, sht21
from sensors.lcd import LCDWriter


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(threadName)s:%(levelname)s:'
                           '%(name)s:%(message)s')
LOGGER = logging.getLogger(__name__)

methods = {'mqtt_publisher': mqtt_publisher.run,
           'coap_server': coap_server.run}

parser = argparse.ArgumentParser(description='Reads data from Dylos sensor')
parser.add_argument('method', choices=methods.keys(),
                    help='Type of transport to use')
parser.add_argument('-c', '--config', type=argparse.FileType('r'),
                    default=open('config.yaml'), help='Configuration file')

args = parser.parse_args()
config = config = yaml.load(args.config)

LOGGER.info("Loading persistent queue")
queue = PersistentQueue('dylos.queue',
                        dumps=msgpack.packb,
                        loads=msgpack.unpackb)

LOGGER.info("Getting host name")
hostname = socket.gethostname()
LOGGER.info("Hostname: %s", hostname)

# Set up sensors
LOGGER.info("Starting LCD screen")
lcd = LCDWriter()

LOGGER.info("Starting air quality sensor")
air_sensor = dylos.setup(config['serial']['port'],
                         config['serial']['baudrate'])

LOGGER.info("Starting temperature sensor")
temp_sensor = sht21.setup()


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

            # Combine data together
            data = {"sampletime": now,
                    "sequence": sequence_number,
                    "monitorname": hostname,
                    **air_data,
                    **temp_data}

            # Transform the data
            # [humidity, large, monitorname, sampletime, sequence, small,
            #  temperature]
            data = [[v for k, v in sorted(data.items())]]

            # Save data for later
            queue.push(data)

            # Display results
            lcd.small = air_data['small']
            lcd.large = air_data['large']
            lcd.update_air_time = datetime.now()
            lcd.queue_size = len(queue)
            lcd.display_data()

        except KeyboardInterrupt:
            break
        except Exception:
            # Keep going no matter of the exception
            # Hopefully it will fix itself
            LOGGER.exception("An exception occurred!")

            LOGGER.debug("Waiting 15 seconds and then trying again")
            time.sleep(15)
            continue


t = Thread(target=read_data)
t.daemon = True
t.start()

# Start server
methods[args.method](config, hostname, queue, lcd)
