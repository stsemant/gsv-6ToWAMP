# -*- coding: utf-8 -*-
__author__ = 'dennis rump'
# Interpret the GSV6 Seriell Kommunikation

from gsv6_serial_lib_errors import *
import logging
import error_codes
import GSV6_BasicFrameType
from struct import *
from anfrage_codes import anfrage_code_to_shortcut


class GSV6_seriall_lib:
    # ist doch so qutasch!!!
    def selectFrameType(self, firstByte):
        if 0 == firstByte:
            # Messwert Frame
            return 0
        elif 1 == firstByte:
            # Antwort
            return 1
        elif 2 == firstByte:
            # Anfrage
            return 2
        else:
            # rise error
            raise GSV6_serial_lib_errors('FrameType not selectable.')

    def stripSerialPreAndSuffix(self, data):
        if (data[-1] == 0x85) and (data[0] == 0xAA):
            del data[-1]
            del data[0]
            return data
        else:
            raise GSV6_Communication_Error('Serial Input from formart (Prefix und suffix).')

    def checkSerialPreAndSuffix(self, data):
        if (data[-1] == 0x85) and (data[0] == 0xAA):
            return 0  # eigentlich nicht nötig, da ja die Exception ausgewertet wird, falls Sie kommt
        else:
            raise GSV6_Communication_Error('Serial Input from formart (Prefix und suffix).')

    def decode_status(self, data):
        inData = bytes(data)

    def encode_anfrage_frame(self, kommando, kommando_para=[]):
        # 0xAA=SyncByte; 0x50=Anfrage,Seriell,Length=0
        result = bytearray([0xAA, 0x90])
        result.append(kommando)
        if len(kommando_para) > 0:
            result.extend(kommando_para)
            # update length
            result[1] = (result[1] | len(kommando_para))
        result.append(0x85)

        return result

    def decode_antwort_frame(self, data):

        inData = bytearray(data)
        # first of all, check data length for minimal length
        if len(inData) < 2:
            raise GSV6_Communication_Error('AntwortFrame too short.')

        data_length = -1

        # check FrameType
        if (inData[0] & 0xC0) != 0x40:
            raise GSV6_Communication_Error('Diffrent FrameType detected, Lib selected AntwortFrame.')
        if not (inData[0] & 0x30 == 0x10):
            raise GSV6_Communication_Error('Diffrent Interface detected, it has to be seriall.')

        data_length = int(inData[0] & 0x0F)
        logging.debug('AntwortFrame Length: ' + str(data_length))

        if inData[1] != 0x00:
            err_code = error_codes.error_code_to_error_shortcut.get(inData[1], 'Error Code not found!.')
            err_msg = error_codes.error_codes_to_messages_DE.get(inData[1], 'Error Code not found!.')
            raise GSV6_ReturnError_Exception(err_code, err_msg)

        # Bis heri keine Fehler aufgetreten, also daten in BasicFrame einbringen für die weitere verarbeitung
        return GSV6_BasicFrameType.BasicFrame(inData)

    def decode_messwert_frame(self, data):

        inData = bytearray(data)
        # first of all, check data length for minimal length
        if len(
                inData) < 3:  # da channel 1 mit 0 angegeben wird, muss mindestens ein channel angegeben werden. Gibt es eine reihnfolge oder wir immer nur ein channel übertragen?
            raise GSV6_Communication_Error('MesswertFrame too short.')

        transmitted_cahnnels = -1

        # check FrameType
        if (inData[0] & 0xC0) != 0x00:
            raise GSV6_Communication_Error('Diffrent FrameType detected, Lib selected MesswertFrame.')
        if not (inData[0] & 0x30 == 0x10):
            raise GSV6_Communication_Error('Diffrent Interface detected, it has to be seriall.')

        transmitted_cahnnels = int(inData[0] & 0x0F)
        logging.debug('MesswertFrame transmitted_cahnnels: ' + str(transmitted_cahnnels))
        '''
        if inData[1] != 0x00:
            err_code = error_codes.error_code_to_error_shortcut.get(inData[1],'Error Code not found!.')
            err_msg = error_codes.error_codes_to_messages_DE.get(inData[1],'Error Code not found!.')
            raise gsv6_serial_lib_errors.GSV6_ReturnError_Exception(err_code, err_msg)

        '''
        # Bis heri keine Fehler aufgetreten, also daten in BasicFrame einbringen für die weitere verarbeitung
        return GSV6_BasicFrameType.BasicFrame(inData)

    # for all conversion see type def in Pytho 2.7
    def convertToUint8_t(self, data):
        length = len(data)
        if not length >= 1:
            raise GSV6_ConversionError_Exception('uint8_t')
            return

        # B	= unsigned char; Python-Type: integer, size:1
        return unpack('>' + str(length) + "B", data)

    def convertToUint16_t(self, data):
        length = len(data)
        if not (length >= 2) and ((length % 2) == 0):
            raise GSV6_ConversionError_Exception('uint16_t')
            return

        # H	= unsigned short; Python-Type: integer, size:2
        return unpack('>' + str(length / 2) + "H", data)

    def convertToU24(self, data):
        raise GSV6_ConversionError_Exception('U24 not yet supported')
        length = len(data)
        if not (length >= 3) and ((length % 3) == 0):
            raise GSV6_ConversionError_Exception('U24')
            return

            # ?	= ?; Python-Type: integer, size:?
            # return unpack(str(length/3)+"?", data)

    def convertToS24(self, data):
        raise GSV6_ConversionError_Exception('S24 not yet supported')
        length = len(data)
        if not (length >= 3) and ((length % 3) == 0):
            raise GSV6_ConversionError_Exception('S24')
            return

            # ?	= ?; Python-Type: integer, size:?
            # return unpack(str(length/3)+"?", data)

    def convertToUint32_t(self, data):
        length = len(data)
        if not (length >= 4) and ((length % 4) == 0):
            raise GSV6_ConversionError_Exception('uint32_t')
            return

        # I	= unsigned int; Python-Type: integer, size:4
        return unpack('>' + str(length / 4) + "I", data)

    def convertToSint32_t(self, data):
        length = len(data)
        if not (length >= 4) and ((length % 4) == 0):
            raise GSV6_ConversionError_Exception('int32_t')
            return

        # i	= int; Python-Type: integer, size:4
        return unpack('>' + str(length / 4) + "i", data)

    # decimal can help here
    def convertToS7_24(self, data):
        raise GSV6_ConversionError_Exception('S7.24 not yet supported')
        length = len(data)
        if not (length >= 4) and ((length % 4) == 0):
            raise GSV6_ConversionError_Exception('S7.24')
            return

        # ?	= ?; Python-Type: integer, size:?
        return unpack('>' + str(length / 4) + "f", data)

    def convertToFloat(self, data):
        length = len(data)
        if not (length >= 4) and ((length % 4) == 0):
            raise GSV6_ConversionError_Exception('float')
            return

        # > = Big-Endian; f	= float; Python-Type: float, size:4
        return unpack('>' + str(length / 4) + "f", data)

    def convertFloatsToBytes(self, data):
        length = len(data)
        if not (length >= 1):
            raise GSV6_ConversionError_Exception('float')
            return

        # > = Big-Endian; f	= float; Python-Type: float, size:4
        return bytearray(pack('>%sf' % len(data), *data))

    def convertToString(self, data):
        length = len(data)
        if not length >= 1:
            raise GSV6_ConversionError_Exception('string')
            return

        # s	= char[]; Python-Type: strng, size:*
        return unpack('>' + str(length) + 's', data)

    def decodeGetInterface(self, data):
        if len(data) < 3:
            raise GSV6_DecodeError_Exception(sys._getframe().f_code.co_name, 'Payload to short.')

        # Protokoll-Type ???

        result = {}

        # 0x3F == <5:0>
        geraete_model = (data[0] & 0x3F)
        if geraete_model == 0x06:
            result['geraete_model'] = 'GSV-6'
        elif geraete_model == 0x08:
            result['geraete_model'] = 'GSV-8'
        else:
            result['geraete_model'] = 'Unbekannt'

        # Messwert-frame-Info
        result['anzahl_messwert-frame-objekte'] = ((data[1] & 0xF0) >> 4)
        if ((data[1] & 0x08) >> 3) == 1:
            result['messuebertragung'] = True
        else:
            result['messuebertragung'] = False
        if (data[1] & 0x07) == 1:
            result['messwertdatentype'] = 'int16'
        elif (data[1] & 0x07) == 2:
            result['messwertdatentype'] = 'int24'
        elif (data[1] & 0x07) == 3:
            result['messwertdatentype'] = 'float32'
        else:
            result['messwertdatentype'] = 'unkown'

        # Schreibschutz
        if ((data[2] & 0x80) >> 7) == 1:
            result['schnittstellen_spezifischer_schreibschutz'] = True
        else:
            result['schnittstellen_spezifischer_schreibschutz'] = False
        if ((data[2] & 0x40) >> 6) == 1:
            result['genereller_schreibschutz'] = True
        else:
            result['genereller_schreibschutz'] = False

        # Deskriptorzahl
        result['deskriptorzahl'] = data[3]

        return result

    def buildGetInterface(self, uebertragung=None):
        if uebertragung is None:
            return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('GetInterface'), [0x00])
        elif uebertragung:
            return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('GetInterface'), [0x02])
        else:
            return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('GetInterface'), [0x01])

    def buildReadAoutScale(self, channelNo):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('ReadAoutScale'), [channelNo])

    def buildWriteAoutScale(self, channelNo, AoutScale):
        data = bytearray([channelNo])
        data.extend(AoutScale)
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('WriteAoutScale'), data)

    def buildReadZero(self, channelNo):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('ReadZero'), [channelNo])

    def buildWriteZero(self, channelNo, zero):
        data = bytearray([channelNo])
        data.extend(zero)
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('WriteZero'), data)

    def buildReadUserScale(self, channelNo):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('ReadUserScale'), [channelNo])

    def buildWriteUserScale(self, channelNo, userScale):
        data = bytearray([channelNo])
        data.extend(userScale)
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('WriteUserScale'), data)

    def buildStartTransmission(self):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('StartTransmission'))

    def buildStopTransmission(self):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('StopTransmission'))

    def buildGetUnitText(self):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('GetUnitText'), [
            0])  # + self.encode_anfrage_frame(anfrage_code_to_shortcut.get(' GetUnitText'),[1])

    def buildSetUnitText(self, text, slot=0):
        if slot <= 0 or slot > 1:
            data = bytearray([0x00, 0x00])
        else:
            data = bytearray([0x01, 0x00])
        data.extend(bytearray(text.encode('ascii', 'replace')))
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('SetUnitText'), data)

    def buildGetUnitNo(self, channelNo):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('GetUnitNo'), [channelNo])

    def buildWriteUnitNo(self, channelNo, unitNo):
        data = bytearray([channelNo])
        data.append(unitNo)
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('SetUnitNo'), data)

    def buildGetSerialNo(self):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('GetSerialNo'))

    def buildGetDeviceHours(self, slot=0):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('GetDeviceHours'), [slot])

    def buildGetDataRate(self):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('ReadDataRate'))

    def buildWriteDataRate(self, dataRate):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('WriteDataRate'), dataRate)

    def buildWriteSaveAll(self, slot=0):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('SaveAll'), [slot])

    def buildWriteSetZero(self, channelNo):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('SetZero'), [channelNo])

    def buildgetFirmwareVersion(self):
        return self.encode_anfrage_frame(anfrage_code_to_shortcut.get('GetFirmwareVersion'))