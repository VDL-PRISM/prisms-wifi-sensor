import asyncio
from datetime import datetime
import json
import logging
import struct

import aiocoap.resource as resource
import aiocoap


LOGGER = logging.getLogger("mqtt_sensor")


class DataResource(resource.Resource):
    def __init__(self, queue, lcd):
        super(DataResource, self).__init__()
        self.queue = queue
        self.lcd = lcd

    async def render_get(self, request):
        LOGGER.debug("Received GET request with payload: %s", request.payload)
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

        # Create and send response
        response = aiocoap.Message(
            code=aiocoap.CONTENT,
            payload=json.dumps({'data': data}).encode('utf-8'))
        return response


def run(config, hostname, queue, lcd):
    # Start server
    try:
        root = resource.Site()
        root.add_resource(('.well-known', 'core'),
                          resource.WKCResource(root.get_resources_as_linkheader))
        root.add_resource(('data',), DataResource(queue, lcd))

        asyncio.async(aiocoap.Context.create_server_context(root))
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        pass
