# -*- coding: utf-8 -*-
from anfrage_codes import anfrage_code_to_shortcut

__author__ = 'dennis rump'

import gsv6_serial_lib_errors
from error_codes import error_code_to_error_shortcut

class BasicFrame:
    frameType = {}
    length_or_channel = {}
    statusbyte = {}
    data = {}

    def __init__(self,data):
        self.data = bytearray(data)
        if len(self.data) < 2:
            raise gsv6_serial_lib_errors.GSV6_DataType_Error('BasicFrameType: need more data to construct.')
        self.frameType = (self.data[0]&0xC0) >> 6
        self.length_or_channel = self.data[0]&0x0F
        self.statusbyte = self.data[1]
        self.data = self.data[2:]

    def getFrameType(self):
        return self.frameType

    def getLength(self):
        return self.length_or_channel

    def getChannelCount(self):
        return self.length_or_channel

    def getStatusByte(self):
        return self.statusbyte

    def getPayload(self):
        return self.data

    def isMesswertSixAchsisError(self):
        if ((self.statusbyte&0x02) >> 1) == 1:
            return True
        else:
            return False

    def isMesswertInputOverload(self):
        if (self.statusbyte&0x01) == 1:
            return True
        else:
            return False

    def getMesswertDataTypeAsString(self):
        type = ((self.statusbyte&0x70)>>4)
        if type == 1:
            return 'int16'
        elif type == 2:
            return 'int24'
        elif type == 3:
            return 'float32'
        else:
            return 'unkown'

    def getAntwortErrorCode(self):
        return self.statusbyte

    def getAntwortErrorText(self):
        return error_code_to_error_shortcut.get(self.statusbyte)

    def toString(self):
        if self.frameType == 0:
            # Messwert Frame
            str = 'MesswertFrame: Kanäle: {} Payload: {} Datentype: {}'.format(self.getChannelCount(), ' '.join(format(z, '02x') for z in self.data), self.getMesswertDataTypeAsString())
            if self.isMesswertSixAchsisError():
                str += ' !6-Achsen-Fehler!'
            if self.isMesswertInputOverload():
                str += ' !Eingang Übersteuert!'
            return str
        elif self.frameType == 1:
            # Antwort Frame
            str = 'AntwortFrame: Länge des Payloads: {} Fehler: {}'.format(self.getLength(), error_code_to_error_shortcut.get(self.statusbyte))
            if self.length_or_channel > 0:
                str += ' Payload: {}'.format(' '.join(format(z, '02x') for z in self.data))
            return str
        else:
            # error
            return 'unkown FrameType.'
