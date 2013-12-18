#!/usr/bin/env python
# Copyright (C) 2011 Ricoh EWS.  All rights reserved.

import os, serial
from ew.util import ew_logging

logger = ew_logging.getLogger("ew.util.ew_hardware")


class FusionCommands:
    PROVISIONED = "AT$QCMIPP?"
    MEID = "at^MEID"
    PROFILE_0 = "AT$QCMIPGETP=0"
    PROFILE_1 = "AT$QCMIPGETP=1"
    MANUFACTURER = "at+CGMI"
    SIGNAL = "at+CSQ"
    SERIAL = "at+GSN"
    MODEL = "at+CGMM"
    SOFTWARE = "at+CGMR"
    FIRMWARE = "at+GMR"
    HARDWARE = "at^hwver"


class Fusion:

    PORT3Gdata = '/dev/ttyUSB0'
    PORT3Gat = '/dev/ttyUSB2'
    SNFILE0 = '/nvram0/serialno.txt'

    def __init__(self):
        self.tablet_id = "Unknown"
        if os.path.exists(self.SNFILE0):
            SN=open(self.SNFILE0)
            self.tablet_id = SN.readline()
        if not os.path.exists(self.PORT3Gat) or not os.path.exists(self.PORT3Gdata):
            raise Exception("Device not available")

        self.serial_command = serial.Serial(self.PORT3Gat, 115200, timeout=0.5)
        if not self.serial_command.isOpen():
            raise Exception("Failed to open serial command")

        self.serial_data = serial.Serial(self.PORT3Gdata, 115200, timeout=0.5)
        if not self.serial_data.isOpen():
            raise Exception("Failed to open serial data")

    def is_provisioned(self):
        result=self.check(FusionCommands.PROVISIONED)
        if result.strip() != "" and int(self.check(FusionCommands.PROVISIONED)) == 1:
            return True
        else:
            return False

    def tablet_id(self):
        return self.tablet_id

    def meid(self):
        meid = ""
        raw_meid = self.check(FusionCommands.MEID)
        if raw_meid.startswith("0x"):
            meid = raw_meid.replace("0x", "")
        return meid.upper()

    def manufacturer(self):
        return self.check(FusionCommands.MANUFACTURER)

    def model(self):
        return self.check(FusionCommands.MODEL)

    def serial(self):
        return self.check(FusionCommands.SERIAL)

    def signal(self):
        return self.check(FusionCommands.SIGNAL)

    def software(self):
        return self.check(FusionCommands.SOFTWARE)

    def firmware(self):
        return self.check(FusionCommands.FIRMWARE)

    def hardware(self):
        return self.check(FusionCommands.HARDWARE)

    def profile_0(self):
        return self.check(FusionCommands.PROFILE_0)

    def profile_1(self):
        return self.check(FusionCommands.PROFILE_1)

    def __close__(self):
        self.serial_command.close()
        self.serial_data.close()

    def catchOK(self):
        response = self.port.read(50) #clear any unsolicited data
        count = len(response)
        while len(response) >= 50:
           response = self.port.read(50)
           count = count + len(response)
        self.port.write("at\r")
        response = self.port.read(200)
        ok_id = response.find('OK') # locate OK response
        count = len(response)
        #    print self.port.self.portstr, UScount,'/',count, "bytes read." ,
        #        print self.port.self.portstr,
        if ok_id < 0:
            logger.error("%r", response)
            return False
        return True

    def check(self, cmd):
        send = cmd + "\r"
        self.serial_data.write(send)
        response = self.serial_data.read(200)
        ok_id = response.find('OK') - 4 # cut out CRLF's
        col_id = response.find(':')
#        # some commands (at least 1) don't give you a colon, they give a LF
#        # so if no colon, find first LF and replace with a colon
        print "response: ", response
        if col_id < 0:
            col_id = 0
            response = response[col_id+1:ok_id]
            ok_id = ok_id + col_id
        ret = response[col_id+1:ok_id]
        if ok_id < 0:
            logger.exception(response)
        return ret
