import asyncio
import json
import logging
import struct
import time

import aiocoap.resource as resource
import aiocoap


LOGGER = logging.getLogger("mqtt_sensor")
CHUNK_SIZE = 20


class DataResource(resource.Resource):
    """
    Example resource which supports GET and PUT methods. It sends large
    responses, which trigger blockwise transfer.
    """

    def __init__(self, queue, lcd):
        super(DataResource, self).__init__()
        self.queue = queue
        self.lcd = lcd

    async def render_get(self, request):
        ack = struct.unpack('I', request.payload)[0]

        # Delete the amount of data that has been ACK'd
        self.queue.delete(ack)

        # Get data from queue
        size = CHUNK_SIZE if len(self.queue) > CHUNK_SIZE else len(self.queue)
        LOGGER.debug("Getting %s from the queue", size)
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
        root.add_resource(('.well-known', 'core'), resource.WKCResource(root.get_resources_as_linkheader))
        root.add_resource(('data',), DataResource(queue, lcd))

        asyncio.async(aiocoap.Context.create_server_context(root))
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        pass

