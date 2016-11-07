import os
import sys
import time

import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.PWM as PWM

LOGGER = logging.getLogger(__name__)

# To properly clock LCD I had to use exotic microsecond range sleep function
usleep = lambda x: time.sleep(x/100000.0) # Can go higher, but will eat up whole CPU on that.
ticks = time.time()
i = 0

class lcd_driver:
    def __init__(self):
        # IOMAP = [RS, CLK(E), B7, B6, B5, B4]
        self.iomap = ["GPIO1_13", "GPIO1_12", "GPIO0_27", "GPIO1_14", "GPIO1_15", "GPIO0_26"]
        # PWMMAP = [R, G, B]
        self.pwmmap = ["P8_34", "P8_45", "P8_46"]
        self.R = "P8_34"
        self.G = "P8_45"
        self.B = "P8_46"

        self.GPIO = GPIO
        for pin in self.iomap:
          self.GPIO.setup(pin, GPIO.OUT)

        #PWM.start(channel, duty, [defautls, unless otherwise stated]freq=2000, polarity=0)
        #duty   0 = on
        #duty 100 = off
        self.PWM = PWM
        for pin in self.pwmmap:
          self.PWM.start(pin, 0)

        LOGGER.debug("Setting Up Screen")

    def setup(self):
        LOGGER.debug("Python HD44780 LCD Driver REV 2")

        # lcdcommand('00000001')

        self.lcdcommand('0011') # \
        self.lcdcommand('0011') # | Initialization Sequence
        self.lcdcommand('0011') # /
        self.lcdcommand('0010') # 4BIT Mode

        # lcdcommand('00001111')

        self.lcdcommand('00000001') # Reset
        self.lcdcommand('00001100') # Dispaly On

      #  lcdcommand('00101000') # number of display lines and character font
      #  lcdcommand('00001000') # Display off
      #  lcdcommand('00000001') # Reset
      #  lcdcommand('00001111') # Display On

        #lcdcommand('11000000') # Shift to 2nd Line
        # Shift Reference
        #10000000  Moves cursor to first address on the left of LINE 1
        #11000000  Moves cursor to first address on the left of LINE 2
        #10010100  Moves cursor to first address on the left of LINE 3
        #11010100  Moves cursor to first address on the left of LINE 4

        LOGGER.debug("Transferring LCD Control to main loop")
        LOGGER.debug('\n')

        LOGGER.debug("Process PID: ")
        LOGGER.debug(str(os.getpid()))
        LOGGER.debug('\n')


    # LCD instruction mode
    # For some reason my LCD takes longer to ACK that mode, hence longer delays.
    def lcdcommand(self, str):
        self.GPIO.output(self.iomap[1], 1)
        usleep(500)
        self.GPIO.output(self.iomap[0], 0)
        iteration = 0
        for idr in str:
            self.GPIO.output(self.iomap[iteration+2], int(idr))
            iteration = iteration + 1
            if iteration == 4:
                iteration = 0
                usleep(100)
                self.GPIO.output(self.iomap[1], 0)
                usleep(100)
                self.GPIO.output(self.iomap[1], 1)
                usleep(500)
        return

  # LCD Data mode
    def lcdprint(self, str):
        for char in str:
            # Binary character value
            bitmap = bin(ord(char))[2:].zfill(8)
            self.GPIO.output(self.iomap[1], 1)
            usleep(20)
            self.GPIO.output(self.iomap[0], 1)
            iteration = 0
            for idr in bitmap:
                self.GPIO.output(self.iomap[iteration+2], int(idr))
                iteration = iteration + 1
                if iteration == 4:
                  iteration = 0
                  usleep(20)
                  self.GPIO.output(self.iomap[1], 0)
                  usleep(20)
                  self.GPIO.output(self.iomap[1], 1)
                  usleep(20)
        return

  #duty   0 = on
  #duty 100 = off
    def setRed(self):
        self.PWM.start(self.R, 0) #R P8_34
        self.PWM.start(self.G, 100) #G P8_45
        self.PWM.start(self.B, 100) #B P8_46

    def setOrange(self):
        self.PWM.start(self.R, 0) #R P8_34
        self.PWM.start(self.G, 50) #G P8_45
        self.PWM.start(self.B, 100) #B P8_46

    def setYellow(self):
        self.PWM.start(self.R, 0) #R P8_34
        self.PWM.start(self.G, 0) #G P8_45
        self.PWM.start(self.B, 100) #B P8_46

    def setGreen(self):
        self.PWM.start(self.R, 100) #R P8_34
        self.PWM.start(self.G, 0) #G P8_45
        self.PWM.start(self.B, 100) #B P8_46

    def setCyan(self):
        self.PWM.start(self.R, 100) #R P8_34
        self.PWM.start(self.G, 0) #G P8_45
        self.PWM.start(self.B, 0) #B P8_46

    def setBlue(self):
        self.PWM.start(self.R, 100) #R P8_34
        self.PWM.start(self.G, 100) #G P8_45
        self.PWM.start(self.B, 0) #B P8_46

    def setPurple(self):
        self.PWM.start(self.R, 50) #R P8_34
        self.PWM.start(self.G, 100) #G P8_45
        self.PWM.start(self.B, 0) #B P8_46

    def setViolet(self):
        self.PWM.start(self.R, 0) #R P8_34
        self.PWM.start(self.G, 100) #G P8_45
        self.PWM.start(self.B, 0) #B P8_46

    def setBlack(self):
        self.PWM.start(self.R, 100) #R P8_34
        self.PWM.start(self.G, 100) #G P8_45
        self.PWM.start(self.B, 100) #B P8_46

    def setGray(self):
        self.PWM.start(self.R, 50) #R P8_34
        self.PWM.start(self.G, 50) #G P8_45
        self.PWM.start(self.B, 50) #B P8_46

    def setWhite(self):
        self.PWM.start(self.R, 0) #R P8_34
        self.PWM.start(self.G, 0) #G P8_45
        self.PWM.start(self.B, 0) #B P8_46

def setup():
    lcd = lcd_driver()
    lcd.setup()

    line1_ = ''
    line2_ = ''

    def write(line1=None, line2=None):
        nonlocal line1_
        nonlocal line2_

        LOGGER.debug("Writing to lcd screen")

        if line1 is not None:
            line1_ = line1

        if line2 is not None:
            line2_ = line2

        LOGGER.debug("Line 1: %s", line1_)
        LOGGER.debug("Line 2: %s", line2_)

        lcd.lcdcommand('00000001')  # Reset
        lcd.lcdprint(line1_)
        lcd.lcdcommand('11000000')  # Move cursor down
        lcd.lcdprint(line2_)
        lcd.lcdcommand('10000000')  # Move cursor to beginning

    return write
