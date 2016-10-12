import time

class sht21:
        def __init__(self):
                pass

        #def get_temp(self):
        #        temp = file('/sys/bus/i2c/drivers/sht21/1-0040/temp1_input')
        #        l = temp.readline().strip()
        #        temp.close()

        #        self.temp = -38.85 + (175.72 * float(l)/65536.0)
        #        self.tempraw = int(l)
        #        return self.temp

        #def get_humidity(self):
        #        humidity = file('/sys/bus/i2c/drivers/sht21/1-0040/humidity1_input')
        #        l = humidity.readline().strip()
        #        humidity.close()
        #        self.humidity = -36 + (125.0 * float(l)/65536.0)
        #        self.humidityraw = int(l)
        #        return self.humidity

        def get_temp(self):
                temp = file('/sys/bus/i2c/drivers/sht21/1-0040/temp1_input')
                l = temp.readline().strip()
                temp.close()

                self.temp = float(l)/1000
                self.tempraw = int(l)

                return self.temp

        def get_humidity(self):
                humidity = file('/sys/bus/i2c/drivers/sht21/1-0040/humidity1_input')
                l = humidity.readline().strip()
                humidity.close()
                
                self.humidity = float(l)/1000
                self.humidityraw = int(l)
                return self.humidity

        def get_tempey(self):
                temp = file('/sys/bus/i2c/drivers/sht21/1-0040/temp1_input')
                l = temp.readline().strip()
                temp.close()

                k = int(l) & 65532

                self.temp = -46.85 + (175.72 * float(k)/65536.0)
                self.tempraw = int(l)
                return self.temp

        def get_humidityey(self):
                humidity = file('/sys/bus/i2c/drivers/sht21/1-0040/humidity1_input')
                l = humidity.readline().strip()
                humidity.close()
                
                k = int(l) & 65532

                self.humidity = -6 + (125.0 * float(k)/65536.0)
                self.humidityraw = int(l)
                return self.humidity

        def get_tempex(self):
                temp = file('/sys/bus/i2c/drivers/sht21/1-0040/temp1_input')
                l = temp.readline().strip()
                temp.close()

                return int(l)

        def get_humidityex(self):
                humidity = file('/sys/bus/i2c/drivers/sht21/1-0040/humidity1_input')
                l = humidity.readline().strip()
                humidity.close()
                return int(l)

if __name__ == "__main__":
        sht = sht21()

        while 1:
                print ("temp {0}C".format(sht.get_temp())) 
                print ("humi {0}".format(sht.get_humidity())) 
                time.sleep(0.5)
