#!/usr/bin/env python
# This program is placed into the public domain by its author, Ian Harvey
# It comes with NO WARRANTY.

import sys, os
import serial
import time
from optparse import OptionParser

def str2hex(blk):
    return " ".join([ "%02X" % ord(ch) for ch in blk ])

class AvrProg:
    # See AVR061 application note, also 'stk500.h' from optiboot source
    STK_OK          = '\x10'
    STK_INSYNC      = '\x14'
    STK_GET_SIGN_ON = '\x30'
    STK_LOAD_ADDRESS= '\x55'
    STK_READ_PAGE   = '\x74'
    STK_WRITE_PAGE  = '\x64'
    CRC_EOP         = '\x20' # Not a CRC at all

    def __init__(self, deviceName, baudrate=115200, isUsb=False):
        self.deviceName = deviceName
        self.port = serial.Serial(self.deviceName, baudrate, timeout=0.5)
        if isUsb:
            self.resetFn = self.reset_RTS
        else:
            self.resetFn = self.reset_GPIO

    def sendCmd(self, cmdBytesNoEOP, retLen=0):
        self.port.write(cmdBytesNoEOP + self.CRC_EOP)
        rv = self.port.read(retLen+2)
        if len(rv) >= 2 and rv[0]==self.STK_INSYNC and rv[-1]==self.STK_OK:
            return (True, rv[1:-1])
        return (False, rv)

    def mustDoCmd(self, cmdBytesNoEOP, retLen=0):
        (ok, msg) = self.sendCmd(cmdBytesNoEOP, retLen)
        if not ok:
            print "Cmd was", [ hex(ord(x)) for x in cmdBytesNoEOP ]
            print "Response was", repr(msg)
            sys.exit("Command returned error\n")
        return msg

    def reset_RTS(self):
        print "Resetting via RTS..."
        self.port.setRTS(False)
    	time.sleep(0.5)
        self.port.flushInput()
        self.port.setRTS(True)

    def reset_GPIO(self, pin=4):
        print "Resetting via GPIO%d..." % pin
        def sendSys(sysfile, data):
            with open(sysfile, "w") as f:
                f.write(data)

        sendSys("/sys/class/gpio/export", str(pin))
        sendSys("/sys/class/gpio/gpio%d/direction" % pin, "out")

        # Set high, wait a bit, then set low
        sendSys("/sys/class/gpio/gpio%d/value" % pin, "0")
        time.sleep(0.2)
        self.port.flushInput()
        sendSys("/sys/class/gpio/gpio%d/value" % pin, "1")
        sendSys("/sys/class/gpio/unexport", str(pin))

    def reset(self):
        self.resetFn()
        # Now try to contact bootloader
        time.sleep(0.2)
        for i in range(10):
            (ok,rv) = self.sendCmd(self.STK_GET_SIGN_ON)
            # AVR061 says it includes a 'sign_on_msg', optiboot just returns 2 bytes
            if ok:
                print "Synced with bootloader"
                return True
            print "Bootloader reponse was:", repr(rv)
        return False

    def _setAddress(self, byteAddr):
        wordAddr = byteAddr/2
        self.mustDoCmd( self.STK_LOAD_ADDRESS + chr(wordAddr & 0xFF) + chr(wordAddr >> 8) )
    
    def _readPage(self, size, memtype = 'F'):
        return self.mustDoCmd( self.STK_READ_PAGE + chr(size >> 8) + chr(size & 0xFF) + memtype, size )

    def readFlash(self, addr, size):
        self._setAddress(addr)
        rv = ''
        while size > 0:
            n = min(size, 32)
            rv += self._readPage(n)
            size -= n
        return rv

    def writeFlashBlock(self, addr, blk, memtype = 'F'):
        print "programming", hex(addr)
        self._setAddress(addr)
        size = len(blk)
        self.mustDoCmd( self.STK_WRITE_PAGE + chr(size >> 8) + chr(size & 0xFF) + memtype + blk, 0)

    def readAll(self, size=32768):
        for i in range(0, size, 16):
            blk = self.readFlash(i, 16)
            print ("%04X: " % i) + str2hex(blk)
        return self

    def loadIntelHex(self, filename):
        self.startAddr = None
        self.loadData = ""
        with open(filename, "r") as f:
            for line in f:
                line = line.rstrip()
                if not line.startswith(":"):
                    sys.exit("Line doesn't start with ':' - not Intel hex?\n" + repr(line))
                line = line[1:]
                (recLen, addr, recType) = [ int(x, 16) for x in (line[0:2], line[2:6], line[6:8]) ]
                if recType == 0x01: # EOF
                    break
                elif recType != 0x00: # Data
                    print "Warning: ignoring record type %02X in file" % recType
                    continue
                if self.startAddr==None:
                    self.startAddr = addr
                elif nextAddr != addr:
                    sys.exit("Input data is not contiguous: hole from %04X..%04X" % (nextAddr, addr))

                data = line[8:-2]
                if len(data) != 2*recLen:
                    sys.exit("Data should contain %d bytes, but was length %d in:\n%s" %
                        (recLen, len(data), line) )
                blk = "".join([ chr(int(data[i:i+2],16)) for i in range(0, 2*recLen, 2) ])
                self.loadData += blk
                nextAddr = addr + len(blk)
        self.fileSize = len(self.loadData)
        return self

    def verify(self):
        errs = 0
        
        for i in range(0,self.fileSize,16):
            want = self.loadData[i:i+16]
            got = self.readFlash(self.startAddr+i, len(want))
            if got != want:
                print "Mismatch at addr", hex(self.startAddr+i)
                print "Want ", str2hex(want)
                print "Got  ", str2hex(got)
                errs += 1

        if errs:
            sys.exit("Verify failed")
        print "Verify OK"
        return self

    def program(self):
        for i in range(0,self.fileSize,128):
            self.writeFlashBlock(self.startAddr+i, self.loadData[i:i+128])
        return self

    def close(self):
        self.port.close()

def ardprog(args):
    parser = OptionParser(usage="usage: %prog [options] [filename]")
    parser.add_option("-t", "--test", action="store_true", dest="test", default=False,
            help="Just test communications with bootloader")
    parser.add_option("-v", "--verify", action="store_true", dest="verify", default=False,
            help="Verify current contents against filename")
    parser.add_option("-r", "--read", action="store_true", dest="read", default=False,
            help="Read contents")
    parser.add_option("-u", "--usb", action="store_true", dest="isUsb", default=False,
            help="Program USB-attached Arduino (default is GPIO)")
    parser.add_option("-p", "--port", action="store", dest="port", default=None,
            help="Set port for bootloader comms")
    parser.add_option(      "--baud", action="store", dest="baud", type="int", default=115200,
            help="Set baud rate")

    (opts, posargs) = parser.parse_args(args)

    if opts.port==None:
        if opts.isUsb:
            opts.port = "/dev/ttyACM0"
        else:
            opts.port = "/dev/ttyAMA0"

    avr = AvrProg(opts.port, opts.baud, opts.isUsb)
    if not avr.reset():
        return "No bootloader found"

    if opts.test:
        print "Bootloader on %s: communications OK" % opts.port
        return 0

    elif opts.read:
        avr.readAll()
        return 0

    elif opts.verify:
        if len(posargs) != 1:
            return "Please supply one filename for verification"
        avr.loadIntelHex(posargs[0])
        avr.verify()

    else:
        if len(posargs) != 1:
            return "Please supply one filename for programming"
        avr.loadIntelHex(posargs[0])
        avr.program()
        avr.verify()
    
if __name__ == '__main__':
    sys.exit( ardprog(sys.argv[1:]) )


