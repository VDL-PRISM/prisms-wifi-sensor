import asyncio
import json
import logging
import os.path
import socket
import struct
import threading
import time

import aiocoap.resource as resource
import aiocoap
from persistent_queue import PersistentQueue
import yaml

from sensors import setup_air_quality, setup_temp_sensor


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
LOGGER = logging.getLogger("mqtt_sensor")
queue = PersistentQueue('queue')
CHUNK_SIZE = 20


class DataResource(resource.Resource):
    """
    Example resource which supports GET and PUT methods. It sends large
    responses, which trigger blockwise transfer.
    """

    def __init__(self):
        super(DataResource, self).__init__()

    @asyncio.coroutine
    def render_get(self, request):
        ack = struct.unpack('I', request.payload)[0]

        # Delete the amount of data that has been ACK'd
        queue.delete(ack)

        # Get data from queue
        size = CHUNK_SIZE if len(queue) > CHUNK_SIZE else len(queue)
        data = queue.peek(size)

        # Create and send response
        response = aiocoap.Message(
            code=aiocoap.CONTENT,
            payload=json.dumps({'data': data}).encode('utf-8'))
        return response


def read_sensors(config):
    LOGGER.info("Starting air quality sensor")
    air_sensor = setup_air_quality(config['serial']['port'],
                                   config['serial']['baudrate'])

    LOGGER.info("Starting temperature sensor")
    temp_sensor = setup_temp_sensor()

    LOGGER.info("Getting host name")
    hostname = socket.gethostname()
    LOGGER.info("Hostname: %s", hostname)

    sequence_number = 0

    # Read from sensors and publish data forever
    while True:
        LOGGER.info("Getting new data")
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

        # Store data for HTTP server
        LOGGER.debug("Putting data into queue")
        queue.push(data)


def run(config_file):
    LOGGER.info("Reading from config")
    config = yaml.load(config_file)

    LOGGER.info("Starting reading from sensors")
    sensor_thread = threading.Thread(target=read_sensors, args=(config,))
    sensor_thread.daemon = True
    sensor_thread.start()

    # Start server
    try:
        root = resource.Site()
        root.add_resource(('.well-known', 'core'), resource.WKCResource(root.get_resources_as_linkheader))
        root.add_resource(('data',), DataResource())

        asyncio.async(aiocoap.Context.create_server_context(root))
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        pass

