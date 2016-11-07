import time

import os
import sys

# To properly clock LCD I had to use exotic microsecond range sleep function
usleep = lambda x: time.sleep(x/100000.0) # Can go higher, but will eat up whole CPU on that. 
# IOMAP = [RS, CLK(E), B7, B6, B5, B4]
#iomap = [GPIO1_12, GPIO0_26, GPIO1_5, GPIO1_31, GPIO2_1, GPIO1_14]



ticks = time.time()
i = 0
class lcd_driver:

  def __init__(self):
    # Set BITMAP of outputs: 
    from bbio import *
    

    # IOMAP = [RS, CLK(E), B7, B6, B5, B4]
    self.iomap = [GPIO1_13, GPIO1_12, GPIO0_27, GPIO1_14, GPIO1_15, GPIO0_26]
    import Adafruit_BBIO.GPIO as GPIO
    self.GPIO = GPIO
    
    for pin in self.iomap:
      self.GPIO.setup(pin, GPIO.OUT)
 
    sys.stdout.write("Setting Up Screen")
    sys.stdout.write('\n')  
    

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

      # Create a setup function:
  def setup(self):

    sys.stdout.write("Python HD44780 LCD Driver REV 2")
    sys.stdout.write('\n')

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
      
    sys.stdout.write("Transferring LCD Control to main loop")
    sys.stdout.write('\n')
    
    sys.stdout.write("Process PID: ")
    sys.stdout.write(str(os.getpid()))
    sys.stdout.write('\n')

if __name__ == '__main__':

  lcd = lcd_driver()

  lcd.clear()
  lcd.lcdprint("LCD Screen")
  lcd.lcdcommand('11000000')
  lcd.lcdprint("__name__ = __main__")
  lcd.lcdcommand('10000000')



