import argparse
import base64
from datetime import datetime
import gzip
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
import logging.handlers
import msgpack
from persistent_queue import PersistentQueue
import pkg_resources
import yaml
import paho.mqtt.client as paho
import time

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

try:
    from Crypto.Cipher import AES
    from Crypto import Random
except:
    LOGGER.debug("Importing package pycrypto")
    subprocess.call([sys.executable, "-m", "pip", "uninstall", "pycrypto"])
    subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade","pip"])
    subprocess.call([sys.executable, "-m", "pip", "install", "pycrypto"])
    from Crypto.Cipher import AES
    from Crypto import Random
    LOGGER.debug("Successfully installed and imported package pycrypto")

class AESCipher(object):

    def __init__(self, key,iv):
        self.bs=16
        self.key = key
        self.iv=iv
        #self.cipher = AES.new(self.key, AES.MODE_CBC, self.iv)

    def encrypt(self, raw):
        raw = self._pad(raw)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return base64.b64encode(cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return self._unpad(cipher.decrypt(enc)).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

# Read data from the sensor
def read_data(output_sensors, input_sensors, queue, cipher):
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
            data = {"sample_time": int(now * 1e6),
                    "data": {"sequence": sequence_number,
                             "queue_length": len(queue) + 1},
                    "metadata": {"firmware": get_firmware_version()}}

            LOGGER.info("Getting new data from sensors")
            for sensor in output_sensors:
                data['data'].update(sensor.read())
            
            # Write data to input sensors
            for sensor in input_sensors:
                sensor.data(data)

            #encrypt data
            data=json.dumps(data)
            LOGGER.debug("Unencrypted data is %s ", data)
            enc_data = cipher.encrypt(data)
            enc_data=enc_data.decode('utf-8')
            now=time.time()
            data = {"data": enc_data, "timestamp":int(now*1e6)}

            # Save data for later
            LOGGER.debug("Pushing %s into queue", data)
            queue.push(data)

            # Every 10 minutes, update time
            if sequence_number % 10 == 0:
                Thread(target=update_clock).start()

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


def get_firmware_version():
    return subprocess.check_output(["git", "describe"]).strip().decode()


def update_clock():
    try:
        LOGGER.debug("Trying to update clock")
        subprocess.run("ntpdate -b -s -u pool.ntp.org", shell=True, check=True, timeout=45)
        LOGGER.debug("Updated to current time")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        LOGGER.warning("Unable to update time")


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

    for component, component_configs in config['sensors'].items():
        # Make sure component_configs is a list
        if component_configs is None:
            component_configs = [None]
        elif isinstance(component_configs, dict):
            component_configs = [component_configs]

        for component_config in component_configs:
            if component == 'device':
                # Ignore device specific configuration: it is not a sensor
                continue

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


def decode_dict(value):
    """Recursively converts dictionary keys to strings."""
    if not isinstance(value, dict):
        if isinstance(value, bytes):
            return value.decode()
        else:
            return value

    return {k.decode(): decode_dict(v) for k, v in value.items()}


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


def on_connect(cli, ud, flag, rc):
    if rc==0:
        LOGGER.info("connected OK rc:" + str(rc))
    else:
        LOGGER.error("Bad connection: Returned code=%s",rc)


def on_publish(client, userdata, mid):
    LOGGER.info("Publish successful: Mid- "+str(mid))


def on_disconnect(cli, ud, rc):
    LOGGER.info("Disconnected: rc-" + str(rc))


def main(config_file):
    # Load config file
    try:
        with open(config_file, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
    except:
        LOGGER.error("Error loading config file")
        exit()

    mqtt_cfg = cfg['mqtt']

    # Load MQTT username and password
    try:
        mqtt_cfg['uname'] = os.environ['MQTT_USERNAME']
        mqtt_cfg['password'] = os.environ['MQTT_PASSWORD']
    except KeyError:
        LOGGER.error("MQTT_USERNAME or MQTT_PASSWORD have not been defined")
        exit()

    input_sensors, output_sensors = load_sensors(config_file)

    for sensor in input_sensors:
        sensor.start()

    def status(message):
        for sensor in input_sensors:
            sensor.status(message)

    # Turn off WiFi
    status("Turning off WiFi")
    try:
        subprocess.run("iwconfig 2> /dev/null | grep -o '^[[:alnum:]]\+' | while read x; do ifdown $x; done",
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
        subprocess.run("iwconfig 2> /dev/null | grep -o '^[[:alnum:]]\+' | while read x; do ifup $x; done",
             shell=True)
    except Exception:
        LOGGER.exception("Exception while turning on WiFi")

    # Wait for 5 seconds
    for i in reversed(range(5)):
        status("Waiting ({})".format(i))
        time.sleep(1)

    try:
        status("Updating clock")
        subprocess.run("ntpdate -b -s -u pool.ntp.org", shell=True, check=True, timeout=120)
        LOGGER.debug("Updated to current time")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        LOGGER.warning("Unable to update time")

    status("Loading queue")
    LOGGER.info("Loading persistent queue")
    queue = PersistentQueue('sensor.queue',
                            dumps=msgpack.packb,
                            loads=msgpack.unpackb)
    bad_queue = PersistentQueue('sensor.bad_queue',
                                dumps=msgpack.packb,
                                loads=msgpack.unpackb)
    #generate key info
    bs = 16
    key = Random.new().read(bs)
    IV = Random.new().read(bs)
    mode = AES.MODE_CBC
    cipher = AESCipher(key, IV)
    now = time.time()
    curr_time=int(now*1e6)
    enc_key=base64.b64encode(key).decode('utf-8')
    enc_iv=base64.b64encode(IV).decode('utf-8')
    

    # Start reading from sensors
    sensor_thread = Thread(target=read_data, args=(output_sensors, input_sensors, queue,cipher))
    sensor_thread.start()

    # Create mqtt client
    client = paho.Client()
    client.username_pw_set(username=mqtt_cfg['uname'], password=mqtt_cfg['password'])
    # Define callabcks
    client.on_connect=on_connect
    client.on_publish = on_publish
    client.on_disconnect=on_disconnect
    # Reconnect interval on disconnect
    client.reconnect_delay_set(3)

    if 'ca_certs' in mqtt_cfg:
        client.tls_set(ca_certs=mqtt_cfg['ca_certs'])

    # Establish client connection
    while True:
        try:
            LOGGER.info("Trying to connect to borker")
            client.connect(mqtt_cfg['server'], mqtt_cfg['port'])
            LOGGER.info("Client connected successfully to broker")
            break
        except:
            LOGGER.exception("Connection failure...trying to reconnect...")
            time.sleep(15)
    client.loop_start()

    # Generate the seesion key and publish it to broker
    try:
        #bs = 16
        #key = Random.new().read(bs)
        #IV = Random.new().read(bs)
        #mode = AES.MODE_CBC
        #cipher = AESCipher(key, IV)
        #curr_time = time.time()
        #enc_key=base64.b64encode(key).decode('utf-8')
        #enc_iv=base64.b64encode(IV).decode('utf-8')
        key_data = {"key": enc_key,"iv": enc_iv,"mode": mode,"timestamp": curr_time}
        key_data = json.dumps(key_data)
        pub_info = client.publish("epifi/v2/{}/key".format(mqtt_cfg['uname']), key_data, qos=1,retain=True)
        pub_info.wait_for_publish()
        while pub_info.rc != 0:
            time.sleep(10)
            pub_info=client.publish("epifi/v2/{}/key".format(mqtt_cfg['uname']), key_data, qos=1,retain=True)
            pub_info.wait_for_publish()
    except Exception as e:
        LOGGER.error("Exception- %s occurred while generating key",e)
        exit()
    
    time.sleep(5)

    # Continuously get data from queue and publish to broker
    while True:
        try:
            LOGGER.info("Waiting for data in queue")
            data = queue.peek(blocking=True)
            data = decode_dict(data)
            data = json.dumps(data)
            info = client.publish("epifi/v2/{}/data".format(mqtt_cfg['uname']), data, qos=1)
            info.wait_for_publish()

            while info.rc != 0:
                time.sleep(10)
                info=client.publish("epifi/v2/{}/data".format(mqtt_cfg['uname']), data, qos=1)
                info.wait_for_publish()

            LOGGER.info("Deleting data from queue")
            queue.delete()
            queue.flush()

            for sensor in input_sensors:
                sensor.transmitted_data(len(queue))

        except KeyboardInterrupt:
            global RUNNING
            RUNNING = False
            for sensor in output_sensors + input_sensors:
                LOGGER.debug("Stopping %s", sensor.name)
                sensor.stop()
            break

        except msgpack.exceptions.UnpackValueError as e:
            LOGGER.exception("Unable to unpack data")
            break

        except Exception as e:
            bad_data=queue.peek()
            LOGGER.error("Exception- %s occurred while listening to data %s", e,str(bad_data))
            LOGGER.info("Pushing data into bad queue")
            error_msg={"message":(str(e)), "data":(str(data))}
            bad_queue.push(error_msg)
            queue.delete()
            queue.flush()

    LOGGER.debug("Waiting for sensor thread")
    sensor_thread.join()
    LOGGER.debug("Shutting down client")
    client.loop_stop()
    LOGGER.debug("Quitting...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generalized WiFi sensor')
    parser.add_argument('-c', '--config', default='configuration.yaml',
                        help='Configuration file. The default is the ' \
                             'configuration.yaml in the current directory.')
    args = parser.parse_args()
    main(args.config)
