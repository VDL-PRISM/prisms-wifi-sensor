import argparse
from datetime import datetime
import json
import logging
import os
import signal
import socket
import struct
import sys
import subprocess
from threading import Thread
import time
from urllib.parse import urlparse

from coapthon.server.coap import CoAP as CoAPServer
from coapthon.resources.resource import Resource
import msgpack
from persistent_queue import PersistentQueue
import pkg_resources
import yaml


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(threadName)s:%(levelname)s:'
                           '%(name)s:%(message)s',
                    handlers=[
                        logging.handlers.TimedRotatingFileHandler(
                            'sensor.log', when='midnight', backupCount=7,
                            delay=True,
                            encoding="utf8"),
                        logging.StreamHandler()])
LOGGER = logging.getLogger(__name__)
RUNNING = True


class DummyResource(Resource):
    def __init__(self):
        super().__init__("DummyResource")


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

            for sensor in self.sensors:
                sensor.transmitted_data(len(self.queue))

            # Get data from queue
            LOGGER.info("Trying to get %s items from the queue", size)
            data = self.queue.peek(size)
            if not isinstance(data, list):
                data = [data]
            LOGGER.info("Got %s items from the queue", len(data))

            # Convert all byte strings to strings
            data = [{key.decode(): (value.decode() if isinstance(value, bytes) else value,
                                    unit.decode()) for key, (value, unit) in d.items()} for d in data]
            LOGGER.debug("Sending data: %s", data)
            self.payload = json.dumps(data)

            return self
        except Exception:
            LOGGER.exception("An error occurred!")


# Read data from the sensor
def read_data(output_sensors, input_sensors, queue):
    sequence_number = 0

    for sensor in input_sensors:
        sensor.status("Starting sensors")

    LOGGER.info("Starting sensors")
    for sensor in output_sensors:
        sensor.start()

    while RUNNING:
        try:
            # Sleep
            for _ in range(60):
                if not RUNNING:
                    break
                time.sleep(1)

            now = time.time()
            sequence_number += 1
            data = {"sampletime": (now, 's'),
                    "sequence": (sequence_number, 'sequence'),
                    "queue_length": (len(queue) + 1, 'num')}

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
                    subprocess.run("ntpdate -b -s -u pool.ntp.org", shell=True, check=True, timeout=45)
                    LOGGER.debug("Updated to current time")
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                    LOGGER.warning("Unable to update time")

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


def load_sensors(config_file):
    import importlib
    sensors = load_sensor_files(config_file)

    input_sensors = []
    output_sensors = []

    for sensor, config in sensors:
        LOGGER.info("Loading %s", sensor)
        module = importlib.import_module(sensor)

        # Make sure module has proper method
        if not hasattr(module, 'setup_sensor'):
            LOGGER.error("Sensor must have setup_sensor function. Skipping...")
            continue

        for req in getattr(module, 'REQUIREMENTS', []):
            if not install_package(req):
                LOGGER.error('Not initializing %s because could not install '
                              'dependency %s', sensor, req)
                continue

        LOGGER.info("Setting up %s", sensor)
        sensor = module.setup_sensor(config)

        if sensor is None:
            LOGGER.error("\"setup_sensor\" returned None, skipping...")
            continue

        if sensor.type == 'input':
            input_sensors.append(sensor)
        elif sensor.type == 'output':
            output_sensors.append(sensor)
        else:
            print('Unknown sensor type')

    return input_sensors, output_sensors


def load_sensor_files(config_file):
    with open(config_file) as f:
        config = yaml.load(f)

    for component, component_configs in config.items():
        # Make sure component_configs is a list
        if component_configs is None:
            component_configs = [None]
        elif isinstance(component_configs, dict):
            component_configs = [component_configs]

        for component_config in component_configs:
            if not os.path.exists(os.path.join('sensors', component)) and \
               not os.path.exists(os.path.join('sensors', component) + '.py'):
                LOGGER.error("Can not find %s", component)
            else:
                yield 'sensors.{}'.format(component), component_config

def check_package_exists(package):
    try:
        req = pkg_resources.Requirement.parse(package)
    except ValueError:
        # This is a zip file
        req = pkg_resources.Requirement.parse(urlparse(package).fragment)

    return any(dist in req for dist in pkg_resources.working_set)


def install_package(package):
    if check_package_exists(package):
        return True

    LOGGER.info('Attempting install of %s', package)
    args = [sys.executable, '-m', 'pip', 'install', package, '--upgrade']
    LOGGER.debug(' '.join(args))

    try:
        return subprocess.call(args) == 0
    except subprocess.SubprocessError:
        LOGGER.exception('Unable to install package %s', package)
        return False


def main(config_file):
    input_sensors, output_sensors = load_sensors(config_file)

    for sensor in input_sensors:
        sensor.start()

    def status(message):
        for sensor in input_sensors:
            sensor.status(message)

    # # Turn off WiFi
    # status("Turning off WiFi")
    # try:
    #     subprocess.run("iwconfig 2> /dev/null | grep -o '^[[:alnum:]]\+' | while read x; do ifdown $x; done",
    #         shell=True)
    # except Exception:
    #     LOGGER.exception("Exception while turning off WiFi")

    # # Wait for 15 seconds
    # for i in reversed(range(15)):
    #     status("Waiting ({})".format(i))
    #     time.sleep(1)

    # # Turn off WiFi
    # status("Turning off WiFi")
    # try:
    #     subprocess.run("iwconfig 2> /dev/null | grep -o '^[[:alnum:]]\+' | while read x; do ifdown $x; done",
    #         shell=True)
    # except Exception:
    #     LOGGER.exception("Exception while turning off WiFi")

    # # Wait for 15 seconds
    # for i in reversed(range(15)):
    #     status("Waiting ({})".format(i))
    #     time.sleep(1)

    # # Turn on WiFi
    # status("Turning on WiFi")
    # try:
    #     subprocess.run("iwconfig 2> /dev/null | grep -o '^[[:alnum:]]\+' | while read x; do ifup $x; done",
    #         shell=True)
    # except Exception:
    #     LOGGER.exception("Exception while turning on WiFi")

    # # Wait for 5 seconds
    # for i in reversed(range(5)):
    #     status("Waiting ({})".format(i))
    #     time.sleep(1)

    # try:
    #     status("Updating clock")
    #     subprocess.run("ntpdate -b -s -u pool.ntp.org", shell=True, check=True, timeout=120)
    #     LOGGER.debug("Updated to current time")
    # except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
    #     LOGGER.warning("Unable to update time")

    status("Loading queue")
    LOGGER.info("Loading persistent queue")
    queue = PersistentQueue('sensor.queue',
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
    server.add_resource('name={}'.format(hostname), DummyResource())

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
    parser = argparse.ArgumentParser(description='Generalized WiFi sensor')
    parser.add_argument('-c', '--config', default='configuration.yaml',
                        help='Configuration file. The default is the ' \
                             'configuration.yaml in the current directory.')
    args = parser.parse_args()
    main(args.config)
