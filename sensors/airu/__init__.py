REQUIREMENTS = ['https://github.com/adafruit/Adafruit_Python_DHT/archive/master.zip#Adafruit_Python_DHT==1.3.2']

def setup_sensor(config):
    from .airstation import AirStation

    return AirStation()
