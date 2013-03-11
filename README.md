arduino-daq
===========

This is a hardware, firmware and software project to add analogue
input and one-wire temperature sensing to a Raspberry Pi. It's
based around an ATMega328 with an Arduino bootloader (see e.g.
part number SC12569 from cpc.farnell.com), so it's extremely easy
to customise.

To avoid the need for any firmware development tools, a pre-built
binary (dlpio8_emu.hex) is provided, together with a tool to load it
via the Arduino bootloader (ardprog.py).

To assist customisation, full source to the ATMega328 firmware
is in the firmware/ directory. You will need an Arduino development
environment to rebuild it, and you'll need to edit the Makefile to
set the path to the tools.

Python source code is provided (daq_dlpio8.py) to communicate with the
ATMega328 via the serial port.

Note
====

The schematic and all software, excluding most of the Makefile and the
OneWire library used by the firmware, were written by Ian Harvey,
2012-2013. These files are placed in the public domain for your
enjoyment.

There is NO WARRANTY of any kind provided with these files.



 
