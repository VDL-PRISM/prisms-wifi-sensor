from __future__ import print_function, division
import logging
from queue import Queue, Empty
from pprint import pprint
import random
import struct
import threading

from coapthon.messages.message import Message
from coapthon import defines
from coapthon.client.coap import CoAP
from coapthon.messages.request import Request
from coapthon.utils import generate_random_token, parse_uri
import msgpack

logging.basicConfig(level=logging.INFO)


class Client(object):
    def __init__(self, server):
        self.server = server
        self.protocol = CoAP(self.server,
                             random.randint(1, 65535),
                             self._wait_response,
                             self._timeout)
        self.queue = Queue()
        self.running = True

    def _wait_response(self, message):
        if message.code != defines.Codes.CONTINUE.number:
            self.queue.put(message)

    def _timeout(self, message):
        self.queue.put(None)

    def stop(self):
        self.running = False
        # self.protocol.stop()
        self.queue.put(None)

    def get(self, path, payload=None):  # pragma: no cover
        request = Request()
        request.destination = self.server
        request.code = defines.Codes.GET.number
        request.uri_path = path
        request.payload = payload

        # Clear out queue before sending a request. It is possible that an old
        # response was received between requests. We don't want the requests
        # and responses to be mismatched. I expect the protocol to take care of
        # that, but I don't have confidence in the CoAP library.
        try:
            while True:
                self.queue.get_nowait()
        except Empty:
            pass

        self.protocol.send_message(request)
        response = self.queue.get(block=True)
        return response

    def multicast_discover(self): # pragma: no cover
        request = Request()
        request.destination = self.server
        request.code = defines.Codes.GET.number
        request.uri_path = defines.DISCOVERY_URL

        self.protocol.send_message(request)
        first_response = self.queue.get(block=True)

        if first_response is None:
            # The message timed out
            return []

        responses = [first_response]
        try:
            # Keep trying to get more responses if they come in
            while self.running:
                responses.append(self.queue.get(block=True, timeout=10))
        except Empty:
            pass

        return responses


def main(path, acks, size, discover):

    if discover:
        try:
            discover_client = Client(server=('224.0.1.187', 5683))
            responses = discover_client.multicast_discover()

            for response in responses:
                print(response.source[0], response.payload)

        except KeyboardInterrupt:
            print("Stopping")
        finally:
            discover_client.stop()

    else:
        try:
            host, port, path = parse_uri(path)
        except Exception:
            print("Not a valid path: {}".format(path))
            print("example: coap://127.0.0.1/data")
            return

        try:
            client = Client(server=(host, port))
            response = client.get(path, payload=struct.pack('!HH', int(acks), int(size)))
            data = msgpack.unpackb(response.payload, use_list=False)
            pprint(data)

        except KeyboardInterrupt:
            print("Stopping")
        finally:
            client.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='CoAP Client')
    parser.add_argument('path', help='Path of CoAP server (coap://host/end_point)')
    parser.add_argument('acks', help='Number of data points to acknowledge')
    parser.add_argument('size', help='Number of data points to get')
    parser.add_argument('-d', '--discover', action='store_true',
                        help='Discover CoAP servers (all other arguments are '
                             'ignored when this is present)')
    args = parser.parse_args()

    main(args.path, args.acks, args.size, args.discover)
