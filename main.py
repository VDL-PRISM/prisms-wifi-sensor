import argparse
from datetime import datetime
import logging
import os
import signal
import socket
import struct
from subprocess import run, check_output, CalledProcessError, TimeoutExpired
from threading import Thread
import time

from coapthon.server.coap import CoAP as CoAPServer
from coapthon.resources.resource import Resource
import msgpack
from persistent_queue import PersistentQueue
import yaml


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(threadName)s:%(levelname)s:'
                           '%(name)s:%(message)s',
                    handlers=[
                        logging.handlers.TimedRotatingFileHandler(
                            'dylos.log', when='midnight', backupCount=7,
                            delay=True),
                        logging.StreamHandler()])
LOGGER = logging.getLogger(__name__)
RUNNING = True


# pylint: disable=abstract-method
class DataResource(Resource):
    def __init__(self, queue, input_sensors):
        super().__init__("DataResource")
        self.queue = queue
        self.sensors = input_sensors

        self.payload = None

    def render_GET(self, request):
        try:
            LOGGER.info("Received GET request with payload: %s",
                         repr(request.payload))
            ack, size = struct.unpack('!HH', request.payload)

            # Delete the amount of data that has been ACK'd
            LOGGER.info("Deleting %s items from the queue", ack)
            self.queue.delete(ack)
            self.queue.flush()

            for sensor in sensors:
                sensor.transmitted_data()

            # Get data from queue
            size = min(size, len(self.queue))
            LOGGER.info("Getting %s items from the queue", size)
            data = self.queue.peek(size)

            # Make sure data is always a list
            if isinstance(data, list) and len(data) > 0 and \
               not isinstance(data[0], list):
                data = [data]

            LOGGER.debug("Sending data: %s", data)
            self.payload = msgpack.packb(data)

            return self
        except Exception:
            LOGGER.exception("An error occurred!")


# Read data from the sensor
def read_data(output_sensors, input_sensors, queue):
    sequence_number = 0

    LOGGER.info("Starting sensors")
    for sensor in output_sensors:
        sensor.start()

    while RUNNING:
        try:
            now = time.time()
            sequence_number += 1
            data = {"sampletime": now,
                    "sequence": sequence_number,
                    "queue_length": len(queue)}

            # TODO: Get IP address
            # TODO: Include device type

            LOGGER.info("Getting new data from sensors")
            for sensor in output_sensors:
                data.update(sensor.read())

            # Save data for later
            LOGGER.debug("Pushing %s into queue", data)
            queue.push(data)

            # Write data to input sensors
            for sensor in input_sensors:
                sensor.data(data)

            # Every 10 minutes, update time
            if sequence_number % 10 == 0:
                try:
                    LOGGER.debug("Trying to update clock")
                    run("ntpdate -b -s -u pool.ntp.org", shell=True, check=True, timeout=45)
                    LOGGER.debug("Updated to current time")
                except (TimeoutExpired, CalledProcessError):
                    LOGGER.warning("Unable to update time")

            for _ in range(60):
                if not RUNNING:
                    break
                time.sleep(1)

        except KeyboardInterrupt:
            break
        except Exception:
            # Keep going no matter of the exception
            # Hopefully it will fix itself
            LOGGER.exception("An exception occurred!")

            if RUNNING:
                LOGGER.debug("Waiting 15 seconds and then trying again")
                time.sleep(15)
                continue

    LOGGER.debug("Exiting read loop")


def load_sensors():
    import importlib
    sensors = load_sensor_files()

    input_sensors = []
    output_sensors = []

    for sensor, config in sensors:
        LOGGER.info("Loading %s", sensor)
        module = importlib.import_module(sensor)

        # Make sure module has proper method
        if not hasattr(module, 'setup_sensor'):
            LOGGER.error("Sensor must have setup_sensor function. Skipping...")
            continue

        if hasattr(module, 'REQUIREMENTS'):
            for req in module.REQUIREMENTS:
                LOGGER.debug("Installing package for %s: %s", sensor, req)
                if not install_package(req):
                    LOGGER.error('Not initializing %s because could not install '
                                  'dependency %s', sensor, req)

        LOGGER.info("Setting up %s", sensor)
        sensor = module.setup_sensor(config)

        if sensor.type == 'input':
            input_sensors.append(sensor)
        elif sensor.type == 'output':
            output_sensors.append(sensor)
        else:
            print('Unknown sensor type')

    return input_sensors, output_sensors


def load_sensor_files():
    with open('configuration.yaml') as f:
        config = yaml.load(f)

    for component, component_configs in config.items():
        # TODO: Make sure component_configs is a list

        for component_config in component_configs:
            if not os.path.exists(os.path.join('sensors', component)) and \
               not os.path.exists(os.path.join('sensors', component) + '.py'):
                LOGGER.error("Can not find %s", component)
            else:
                yield 'sensors.{}'.format(component), component_config


def install_package(package):
    LOGGER.info('Attempting install of %s', package)
    args = [sys.executable, '-m', 'pip', 'install', package, '--upgrade']

    try:
        LOGGER.info('-' * 80)
        result = subprocess.call(args) == 0
        LOGGER.info('-' * 80)
        return result
    except subprocess.SubprocessError:
        LOGGER.exception('Unable to install pacakge %s', package)
        LOGGER.info('-' * 80)
        return False


def main():
    input_sensors, output_sensors = load_sensors()

    for sensor in input_sensors:
        sensor.start()

    def status(message):
        for sensor in input_sensors:
            sensor.status(message)

    # Turn off WiFi
    status("Turning off WiFi")
    try:
        run("iwconfig 2> /dev/null | grep -o '^[[:alnum:]]\+' | while read x; do ifdown $x; done",
            shell=True)
    except Exception:
        LOGGER.exception("Exception while turning off WiFi")

    # Wait for 15 seconds
    for i in reversed(range(15)):
        status("Waiting ({})".format(i))
        time.sleep(1)

    # Turn off WiFi
    status("Turning off WiFi")
    try:
        run("iwconfig 2> /dev/null | grep -o '^[[:alnum:]]\+' | while read x; do ifdown $x; done",
            shell=True)
    except Exception:
        LOGGER.exception("Exception while turning off WiFi")

    # Wait for 15 seconds
    for i in reversed(range(15)):
        status("Waiting ({})".format(i))
        time.sleep(1)

    # Turn on WiFi
    status("Turning on WiFi")
    try:
        run("iwconfig 2> /dev/null | grep -o '^[[:alnum:]]\+' | while read x; do ifup $x; done",
            shell=True)
    except Exception:
        LOGGER.exception("Exception while turning on WiFi")

    # Wait for 5 seconds
    for i in reversed(range(5)):
        status("Waiting ({})".format(i))
        time.sleep(1)

    try:
        status("Updating clock")
        run("ntpdate -b -s -u pool.ntp.org", shell=True, check=True, timeout=120)
        LOGGER.debug("Updated to current time")
    except (TimeoutExpired, CalledProcessError):
        LOGGER.warning("Unable to update time")

    status("Loading queue")
    LOGGER.info("Loading persistent queue")
    queue = PersistentQueue('dylos.queue',
                            dumps=msgpack.packb,
                            loads=msgpack.unpackb)

    LOGGER.info("Getting host name")
    hostname = socket.gethostname()
    LOGGER.info("Hostname: %s", hostname)

    # Start reading from sensors
    sensor_thread = Thread(target=read_data,
                           args=(output_sensors, input_sensors, queue))
    sensor_thread.start()

    # Start server
    LOGGER.info("Starting server")
    server = CoAPServer(("224.0.1.187", 5683), multicast=True)
    server.add_resource('data/', DataResource(queue, input_sensors))

    while True:
        try:
            server.listen()
        except KeyboardInterrupt:
            global RUNNING

            RUNNING = False
            LOGGER.debug("Shutting down server")
            server.close()

            for sensor in output_sensors + input_sensors:
                LOGGER.debug("Stopping %s", sensor.name)
                sensor.stop()

            break
        except Exception as e:
            LOGGER.error("Exception occurred while listening: %s", e)


    LOGGER.debug("Waiting for sensor thread")
    sensor_thread.join()
    LOGGER.debug("Quitting...")

if __name__ == '__main__':
    main()
