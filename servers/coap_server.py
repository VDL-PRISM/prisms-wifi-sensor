from __future__ import print_function, division
from datetime import datetime
import json
import logging
import struct

from coapthon.server.coap import CoAP as CoAPServer
from coapthon.resources.resource import Resource
import msgpack


LOGGER = logging.getLogger("mqtt_sensor")

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
            LOGGER.debug("Received GET request with payload: %s", repr(request.payload))
            ack, size = struct.unpack('!HH', request.payload)

            # Delete the amount of data that has been ACK'd
            LOGGER.debug("Deleting %s items from the queue", ack)
            self.queue.delete(ack)

            # TODO: Think about when to flush this
            # self.queue.flush()

            LOGGER.debug("Updating LCD")
            self.lcd.queue_size = len(self.queue)
            self.lcd.update_queue_time = datetime.now()
            self.lcd.display_data()

            # Get data from queue
            size = min(size, len(self.queue))
            LOGGER.debug("Getting %s items from the queue", size)
            data = self.queue.peek(size)

            # Make sure data is always a list
            if not isinstance(data, list):
                data = [data]

            # Transform data
            data = [[v for k, v in sorted(d.items())] for d in data]
            self.payload = msgpack.packb(data)

            return self
        except Exception:
            LOGGER.exception("An error occurred!")

def run(config, hostname, queue, lcd):
    # Start server
    try:
        server = CoAPServer(("224.0.1.187", 5683), multicast=True)
        server.add_resource('air_quality/', AirQualityResource(queue, lcd))
        server.listen()
    except KeyboardInterrupt:
        LOGGER.debug("Shutting down server")
        server.close()


