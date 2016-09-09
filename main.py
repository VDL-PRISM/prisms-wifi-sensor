import argparse
import mqtt_publisher
import http_server

methods = {'mqtt_publisher': mqtt_publisher.run,
           'http_server': http_server.run}

parser = argparse.ArgumentParser(description='Reads data from Dylos sensor')
parser.add_argument('method', choices=methods.keys(),
                    help='Type of transport to use')
parser.add_argument('-c', '--config', type=argparse.FileType('r'),
                    default=open('config.yaml'), help='Configuration file')

args = parser.parse_args()
methods[args.method](args.config)

