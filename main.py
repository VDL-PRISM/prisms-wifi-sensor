from __future__ import print_function, division
import argparse
from datetime import datetime
import logging
import socket
import struct
from threading import Thread
import time

from coapthon.server.coap import CoAP as CoAPServer
from coapthon.resources.resource import Resource
import msgpack
from persistent_queue import PersistentQueue
import yaml

from sensors import dylos, sht21
from sensors.lcd import LCDWriter

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(threadName)s:%(levelname)s:'
                           '%(name)s:%(message)s')
LOGGER = logging.getLogger(__name__)


# pylint: disable=abstract-method
class AirQualityResource(Resource):
    def __init__(self, queue, lcd):
        super(AirQualityResource, self).__init__("AirQualityResource")
        self.queue = queue
        self.lcd = lcd
        self.resource_type = "rt1"
        self.content_type = "text/plain"
        self.interface_type = "if1"

        self.payload = None

    def render_GET(self, request):
        try:
            LOGGER.debug("Received GET request with payload: %s",
                         repr(request.payload))
            ack, size = struct.unpack('!HH', request.payload)

            # Delete the amount of data that has been ACK'd
            LOGGER.debug("Deleting %s items from the queue", ack)
            self.queue.delete(ack)
            self.queue.flush()

            LOGGER.debug("Updating LCD")
            self.lcd.queue_size = len(self.queue)
            self.lcd.update_queue_time = datetime.now()
            self.lcd.display_data()

            # Get data from queue
            size = min(size, len(self.queue))
            LOGGER.debug("Getting %s items from the queue", size)
            data = self.queue.peek(size)

            # Make sure data is always a list
            if isinstance(data, list) and not isinstance(data[0], list):
                data = [data]

            self.payload = msgpack.packb(data)

            return self
        except Exception:
            LOGGER.exception("An error occurred!")


# Read data from the sensor
def read_data(config, lcd, queue):
    LOGGER.info("Getting host name")
    hostname = socket.gethostname()
    LOGGER.info("Hostname: %s", hostname)

    LOGGER.info("Starting air quality sensor")
    air_sensor = dylos.setup(config['serial']['port'],
                             config['serial']['baudrate'])

    LOGGER.info("Starting temperature sensor")
    temp_sensor = sht21.setup()

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

def main():
    parser = argparse.ArgumentParser(description='Reads data from Dylos sensor')
    parser.add_argument('-c', '--config', type=argparse.FileType('r'),
                        default=open('config.yaml'), help='Configuration file')

    args = parser.parse_args()
    config = yaml.load(args.config)

    LOGGER.info("Loading persistent queue")
    queue = PersistentQueue('dylos.queue',
                            dumps=msgpack.packb,
                            loads=msgpack.unpackb)

    # Set up sensors
    LOGGER.info("Starting LCD screen")
    lcd = LCDWriter()

    # Start reading from sensors
    sensor_thread = Thread(target=read_data, args=(config, lcd, queue))
    sensor_thread.daemon = True
    sensor_thread.start()

    # Start server
    try:
        LOGGER.info("Starting server")
        server = CoAPServer(("224.0.1.187", 5683), multicast=True)
        server.add_resource('air_quality/', AirQualityResource(queue, lcd))
        server.listen()
    except KeyboardInterrupt:
        LOGGER.debug("Shutting down server")
        server.close()


if __name__ == '__main__':
    main()
