import serial
import time
import sys
import os
import math

class DLPIO8:
    NUM_CHANNELS = 8
    
    def __init__(self, deviceName):
        self.deviceName = deviceName
        self.port = serial.Serial(self.deviceName, baudrate=115200, timeout=5)
        for i in range(10):
            if self._checkPresent():
                break
        self.setTempC()
        
    def debug(self, what):
        print "DLPIO8:", what
       
    def _checkPresent(self):
        self.debug("Checking device")
        self.port.flushInput()
        self.port.write("'")
        rv = self.port.read(1)
        if len(rv) < 1:
            self.debug("No reply from %s" % self.deviceName)
            return False
        if rv != 'Q':
            self.debug("Device returned '%s' to ping command" % rv)
            return False

        return True

    def setTempC(self):
        self.port.write(';')

    def setTempF(self):
        self.port.write('L')

    def _readLine(self):
        # DAQ sends us \n\r line endings, make sure we swallow them
        rv = self.port.readline() + self.port.read(1)
        return rv.rstrip()
        
    def readVin(self, channel):
        self.port.write( "ZXCVBNM,"[channel-1] )
        rv = self._readLine()
        assert(rv.endswith("V"))
        return float(rv.rstrip("V"))

    def readVACrms(self, channel, nsamples=100):
        samples = [ self.readVin(channel) for i in range(nsamples) ]
        mean = sum(samples) / float(nsamples)
        meansq = sum([x*x for x in samples]) / float(nsamples)
        return math.sqrt(meansq - mean*mean)
        
    def readTemp(self, channel):
        self.port.write( "90-=OP[]"[channel-1] )
        rv = self._readLine()
        if not(rv.endswith("\xf8C") or rv.endswith("\xf8F")):
            print "Temp channel", channel, "gave", repr(rv)
            return None
        if rv.startswith('999'):
            return None
        temp=float(rv[0:-2])
        if rv.endswith("C"):
            return temp
        else:
            return (temp-32.0)*(5.0/9.0)

def tostr(v, fmt="%.1f"):
    if v is None:
        return "None"
    return fmt % v

if __name__ == '__main__':
    daq = DLPIO8("/dev/ttyAMA0")

    for i in range(1,5):
        print "Temp channel",i,"is", daq.readTemp(i)

    for i in range(1,7):
        print "ADC channel",i,"is", daq.readVin(i)

