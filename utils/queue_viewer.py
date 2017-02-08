import argparse
from datetime import datetime

import msgpack
from persistent_queue import PersistentQueue
import pytz
from tabulate import tabulate


parser = argparse.ArgumentParser(description='View data from a queue')
parser.add_argument('queue')
parser.add_argument('start', type=int)
parser.add_argument('end', type=int)
args = parser.parse_args()

file = args.queue
start = args.start
end = args.end

queue = PersistentQueue(file,
                        dumps=msgpack.packb,
                        loads=msgpack.unpackb)

if end == 0:
    data = queue.peek(len(queue))
else:
    data = queue.peek(end)

data = data[start:]

data = [(humidity, large, datetime.utcfromtimestamp(sampletime).replace(tzinfo=pytz.utc), sequence, small, temperature)
        for humidity, large, sampletime, sequence, small, temperature  in data]

table = tabulate(data, headers=["Humidity", "Large", "Sample Time",
                                "Sequence", "Small", "Temperature"])
print(table)
