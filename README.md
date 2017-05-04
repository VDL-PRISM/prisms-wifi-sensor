# Utah Modified Dylos Code

This code reads air quality data from the Dylos serial port, temperature and humidity from the SHT21 sensor, and writes information to an LCD screen. The only mandatory sensor is the Dylos -- all other sensors will gracefully fail if not connected. There are a few software sensors as well: local ping (pings the gateway), remote ping (pings our server), and wireless (captures wireless stats).

It creates a CoAP server with the endpoint `air-quality`.

```
GET coap://<device>/air_quality
```

In the request payload, **two integers need to be included**. These integers should be the number of data points to acknowledge and how many data point to send. See `utils/coap_client.py` as an example. The result of this request is a list of data samples, in the following format:

```
[
    [associated, data_rate, humidity, invalid_misc, large, link_quality, local_ping_errors, local_ping_latency, local_ping_packet_loss, local_ping_total, noise_level, remote_ping_errors, remote_ping_latency, remote_ping_packet_loss, remote_ping_total, rx_invalid_crypt, rx_invalid_frag, rx_invalid_nwid, sampletime, sequence, signal_level, small, temperature, tx_retires]
    ...
]

```


It also supports the `.well-known/core` endpoint for resource discovery.

```
GET coap://<device>/.well-known/core
```

This returns all of the resources available from the Dylos sensor. For example:

```
</air_quality>;</name=monitorX>;</type=dylos-2>;
```

shows the `air_quality` endpoint, the name of the sensor (hostname) and type of sensor.

The CoAP server also binds to the CoAP multicast address (`224.0.1.187`), which means it response to multicast requests. This works well for discovery.


The code has been tested using Python 3.5. To run,

```bash
python3 main.py
```

This starts the CoAP server and starts reading from the sensors.
