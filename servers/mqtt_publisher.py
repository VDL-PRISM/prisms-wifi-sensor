from datetime import datetime
import json
import logging
import time

import paho.mqtt.client as mqtt

LOGGER = logging.getLogger(__name__)


def run(config, hostname, queue, lcd):
    mqtt_config = config['mqtt']
    connect_counter = 1

    def do_publish(client, queue):
        LOGGER.info("Waiting for data on the queue")
        data = queue.peek(blocking=True)
        LOGGER.info("Publishing data: %s", data)
        client.publish(mqtt_config['topic'] + hostname, json.dumps(data),
                       mqtt_config['qos'])

    # pylint: disable=unused-argument
    def on_connect(client, queue, flags, result_code):
        LOGGER.info("Connected to MQTT broker")
        do_publish(client, queue)

    def on_publish(client, queue, mid):
        LOGGER.info("Published finished (MID: %s)", mid)

        # Remove the data that was just published
        queue.delete()

        if mid % 100 == 0:
            queue.flush()

        # Update LCD
        lcd.queue_size = len(queue)
        lcd.update_queue_time = datetime.now()
        lcd.display_data()

        # Try publishing the next message
        do_publish(client, queue)

    while True:
        try:
            LOGGER.info("Connecting to MQTT broker")
            lcd.display(line2="Connecting ({})".format(connect_counter))

            client = mqtt.Client(client_id=hostname,
                                 userdata=queue,
                                 clean_session=False)
            client.username_pw_set(mqtt_config['username'],
                                   mqtt_config['password'])

            client.on_publish = on_publish
            client.on_connect = on_connect

            client.connect(mqtt_config['broker'], mqtt_config['port'])
            lcd.display(line2="Connected!")

            client.loop_forever()

        except KeyboardInterrupt:
            LOGGER.debug("Cleaning up MQTT publisher")
            queue.flush()
            break
        except Exception:
            # Keep going no matter of the exception
            # Hopefully it will fix itself
            LOGGER.exception("An exception occurred!")
            LOGGER.warning("Sleeping for 30 seconds and trying again...")
            lcd.display(line2="Waiting...")
            connect_counter += 1

            time.sleep(30)
            continue
