# Utah Modified Dylos Code

This code reads air quality data from the Dylos serial port, temperature and humidity from the SHT21 sensor, and writes information to an LCD screen. The only mandatory sensor is the Dylos -- all other sensors will gracefully fail if not connected.

It creates a CoAP server with the endpoint `air-quality`.

```
GET coap://<device>/air_quality
```

In the request payload, **two integers need to be included**. These integers should be the number of data points to acknowledge and how many data point to send. See `utils/coap_client.py` as an example. The result of this request is a list of data samples, in the following format:

```
[
    [humidity, large, sampletime, sequence, small, temperature],
    ...
]

```


It also supports the `.well-known/core` endpoint for resource discovery.

```
GET coap://<device>/.well-known/core
```

This returns all of the resources available from the Dylos sensor. For example:

```
</air_quality>;</name=monitorX>;</type=dylos>;
```

shows the `air_quality` endpoint, the name of the sensor (hostname) and type of sensor.

The CoAP server also binds to the CoAP multicast address (`224.0.1.187`), which means it response to multicast requests. This works well for discovery.


The code has been tested using Python 3.5. To run,

```bash
python3 main.py
```

This starts the CoAP server and starts reading from the sensors.
