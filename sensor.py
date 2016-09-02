import json
import logging
import os
import socket
import time

import Adafruit_BBIO.UART as UART
from driver.sht_driver import sht21
import paho.mqtt.client as mqtt
import serial
import yaml


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
LOGGER = logging.getLogger("air_sensor")


def setup_air_quality(port, baudrate):
    # Setup UART
    UART.setup("UART1")

    ser = serial.Serial(port=port, baudrate=baudrate,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS)
    ser.open()

    def read():
        line = ser.readline()
        small, large = [int(x) for x in line.split(',')]
        LOGGER.debug("Read from serial port: %s %s", small, large)
        return {"small": small, "large": large}

    return read


def setup_temp_sensor():
    try:
        sht = sht21()
        sht.get_temp()
    except IOError:
        LOGGER.debug("No sht sensor available")
        sht = None

    def read():
        if sht is None:
            return {"temperature": None, "humidity": None}

        LOGGER.debug("Reading from sht sensor")
        return {"temperature": round(sht.get_temp()),
                "humidity": round(sht.get_humidity())}

    return read


def run():
    LOGGER.info("Reading from config")
    config = yaml.load(open('config.yaml'))
    mqtt_config = config['mqtt']

    LOGGER.info("Starting air quality sensor")
    air_sensor = setup_air_quality(config['serial']['port'],
                                   config['serial']['baudrate'])

    LOGGER.info("Starting temperature sensor")
    temp_sensor = setup_temp_sensor()

    LOGGER.info("Getting host name")
    hostname = socket.gethostname()
    LOGGER.info("Hostname: %s", hostname)

    LOGGER.info("Connecting to MQTT broker")
    client = mqtt.Client(client_id=hostname, clean_session=False)
    client.username_pw_set(mqtt_config['username'], mqtt_config['password'])
    client.connect(mqtt_config['broker'], mqtt_config['port'])

    # Read from sensors and publish data forever
    try:
        client.loop_start()
        sequence_number = 0

        while True:
            LOGGER.info("Getting new data")
            air_data = air_sensor()
            temp_data = temp_sensor()
            now = time.time()
            sequence_number += 1

            # combine data together
            data = {"sampletime": now,
                    "sequence": sequence_number,
                    "monitorname": hostname}
            data.update(air_data)
            data.update(temp_data)

            # Send to MQTT
            LOGGER.info("Publishing new data: %s", data)
            client.publish(mqtt_config['topic'] + hostname, json.dumps(data),
                           mqtt_config['qos'])
    except KeyboardInterrupt:
        client.loop_stop()


if __name__ == '__main__':
    run()
