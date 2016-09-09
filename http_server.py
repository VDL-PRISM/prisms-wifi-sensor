import logging
import socket
import threading
import time

from flask import Flask, jsonify
from persistent_queue import PersistentQueue
import yaml

from sensors import setup_air_quality, setup_temp_sensor

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
LOGGER = logging.getLogger("mqtt_sensor")
app = Flask(__name__)
queue = PersistentQueue('queue')
CHUNK_SIZE = 100


@app.route("/")
def get_data():
    data = []
    size = CHUNK_SIZE if len(queue) > CHUNK_SIZE else len(queue)

    LOGGER.debug("Getting data from queue")
    # Warning: the data is being removed from the queue so if for some reason
    # the response doesn't get received, the data will be gone. This is not an
    # ideal solution.
    data = queue.pop(size)
    return jsonify(data=data)


def run(config_file):
    LOGGER.info("Reading from config")
    config = yaml.load(config_file)
    http_config = config['http']

    LOGGER.info("Starting air quality sensor")
    air_sensor = setup_air_quality(config['serial']['port'],
                                   config['serial']['baudrate'])

    LOGGER.info("Starting temperature sensor")
    temp_sensor = setup_temp_sensor()

    LOGGER.info("Getting host name")
    hostname = socket.gethostname()
    LOGGER.info("Hostname: %s", hostname)

    LOGGER.info("Starting to HTTP server")
    server_thread = threading.Thread(target=app.run,
                                     kwargs={'debug': False,
                                             'port': http_config['port']})
    server_thread.daemon = True
    server_thread.start()

    # Read from sensors and publish data forever
    try:
        sequence_number = 0

        while True:
            LOGGER.info("Getting new data")
            air_data = air_sensor()
            temp_data = temp_sensor()

            now = time.time()
            sequence_number += 1

            # Combine data together
            data = {"sampletime": now,
                    "sequence": sequence_number,
                    "monitorname": hostname}
            data.update(air_data)
            data.update(temp_data)

            # Store data for HTTP server
            LOGGER.debug("Putting data into queue")
            queue.push(data)
    except KeyboardInterrupt:
        pass

