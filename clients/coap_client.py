import asyncio
import json
import logging
from pprint import pprint
import struct

from aiocoap import *

logging.basicConfig(level=logging.INFO)

async def main(address, acks, size):
    protocol = await Context.create_client_context()

    request = Message(code=GET, payload=struct.pack('!HH', acks, size))
    request.set_request_uri('coap://{}/data'.format(address))

    try:
        response = await protocol.request(request).response
    except Exception as e:
        print('Failed to fetch resource:')
        print(e)
    else:
        # print('Result: %s\n%r'%(response.code, response.payload))
        data = json.loads(response.payload.decode('utf-8'))
        pprint(data)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("{} ip_address acks size".format(__file__))
    else:
        asyncio.get_event_loop().run_until_complete(main(sys.argv[1],
                                                         int(sys.argv[2]),
                                                         int(sys.argv[3])))
