# -*- coding: utf-8 -*-
from GSV6_SerialLib_errors import GSV6_ConversionError_Exception, GSV6_Communication_Error, GSV6_ReturnError_Exception

__author__ = 'Dennis Rump'
###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) 2015 Dennis Rump
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Hiermit wird unentgeltlich, jeder Person, die eine Kopie der Software
# und der zugehörigen Dokumentationen (die "Software") erhält, die
# Erlaubnis erteilt, uneingeschränkt zu benutzen, inklusive und ohne
# Ausnahme, dem Recht, sie zu verwenden, kopieren, ändern, fusionieren,
# verlegen, verbreiten, unter-lizenzieren und/oder zu verkaufen, und
# Personen, die diese Software erhalten, diese Rechte zu geben, unter
# den folgenden Bedingungen:
#
# Der obige Urheberrechtsvermerk und dieser Erlaubnisvermerk sind in
# alle Kopien oder Teilkopien der Software beizulegen.
#
# DIE SOFTWARE WIRD OHNE JEDE AUSDRÜCKLICHE ODER IMPLIZIERTE GARANTIE
# BEREITGESTELLT, EINSCHLIESSLICH DER GARANTIE ZUR BENUTZUNG FÜR DEN
# VORGESEHENEN ODER EINEM BESTIMMTEN ZWECK SOWIE JEGLICHER
# RECHTSVERLETZUNG, JEDOCH NICHT DARAUF BESCHRÄNKT. IN KEINEM FALL SIND
# DIE AUTOREN ODER COPYRIGHTINHABER FÜR JEGLICHEN SCHADEN ODER SONSTIGE
# ANSPRUCH HAFTBAR ZU MACHEN, OB INFOLGE DER ERFÜLLUNG VON EINEM
# VERTRAG, EINEM DELIKT ODER ANDERS IM ZUSAMMENHANG MIT DER BENUTZUNG
# ODER SONSTIGE VERWENDUNG DER SOFTWARE ENTSTANDEN.
#
###############################################################################
# Unittest for GSV6_SeriellLib

import unittest
import GSV6_SeriallLib


def getMesswertFrame(messwerte=True, interface_ok=True, frame_type_ok=True):
    # 0xAA        # Serial start
    # 0b00        # Messwert Frame
    # 0b01        # Interface -> Serial
    # 0b0000      # Anzahl der Kanaele -> 5 -> 1001
    # 0b10010000  # Steuerbyte / Statusbyte indikato <7>=1 <6:4>=001 (int16) <3:0>=0 (kein Error)
    # 481         # Data    -> da int 16 zwei byte -> 0x00 0x01
    # 0x85        # Serial ende

    # => 0xAA 0001 0001 1001 0000  0x00 0x01 0x85
    # => 0xAA    0x11      0x90    0x00 0x01 0x85

    frametype = 0x00
    interface = 0x01
    length = 1

    if not frame_type_ok:
        frametype = 0x01
    if not interface_ok:
        interface = 0x00
    if not messwerte:
        length = 0

    secondByte = ((frametype << 6) | (interface << 4)) | length

    result = bytearray([secondByte, 0x90])
    if messwerte:
        result.extend([0x00, 0x01])
    return result


def getAnwortFrame(data={}, error_code=0x00, interface_ok=True, frame_type_ok=True):
    # 0xAA        # Serial start
    # 0b01        # Anwort Frame
    # 0b01        # Interface -> Serial
    # 0b0000      # Payload Length
    # 0b00000000  # Steuerbyte / Statusbyte indikato <7>=1 <6:4>=001 (int16) <3:0>=0 (kein Error)
    # 481         # Data    -> da int 16 zwei byte -> 0x00 0x01
    # 0x85        # Serial ende

    # => 0xAA 0101 xxxx  1001 0000 x 0x85
    # => 0xAA    0x5?      0x50    x 0x85

    payload = bytearray(data)
    length = int(len(payload))

    frametype = 0x01
    interface = 0x01
    if not frame_type_ok:
        frametype = 0x00
    if not interface_ok:
        interface = 0x00

    # secondByte = 0x50 | length
    secondByte = ((frametype << 6) | (interface << 4)) | length

    # result = bytearray([0xAA,secondByte,error_code])
    result = bytearray([secondByte, error_code])
    result.extend(payload)
    # result.append(0x85)
    return result


class TestGSV6_SeriellLib(unittest.TestCase):
    def setUp(self):
        self.gsv6 = GSV6_SeriallLib.GSV6_seriall_lib()

    def tearDown(self):
        self.gsv6 = None

    def test_convertByteToFloat_fail(self):
        # less tha four bytes
        wrong_float_data = bytearray([0x3f, 0x80, 0x00])

        with self.assertRaises(GSV6_ConversionError_Exception) as context:
            self.gsv6.convertToFloat(wrong_float_data)

    def test_convertByteToFloat_ok(self):
        float_data = bytearray([0x3f, 0x80, 0x00, 0x00])

        value = self.gsv6.convertToFloat(float_data)
        self.assertEqual(1.0, value[0])

    def test_convertFloatToByte_fail(self):
        # less tha four bytes
        with self.assertRaises(Exception) as context:
            self.gsv6.convertFloatsToBytes(["test"])

    def test_convertFloatToByte_ok_1(self):
        self.gsv6.convertFloatsToBytes([22.2])

    def test_convertFloatToByte_ok_2(self):
        self.gsv6.convertFloatsToBytes([22])

    def test_convertByteToUInt32_fail(self):
        # less tha four bytes
        wrong_data = bytearray([0x00, 0x00, 0x01])

        with self.assertRaises(GSV6_ConversionError_Exception) as context:
            self.gsv6.convertToUint32_t(wrong_data)

    def test_convertByteToUInt32_ok(self):
        data = bytearray([0x00, 0x00, 0x00, 0x01])
        self.gsv6.convertToUint32_t(data)

    def test_decode_antwortFrame_ok_1(self):
        payload = bytearray([0x33, 0x44])
        payloadLength = len(payload)
        data = getAnwortFrame(payload, error_code=0x00, interface_ok=True, frame_type_ok=True)

        frame = self.gsv6.decode_antwort_frame(data)

        self.assertEqual(frame.getLength(), payloadLength)
        self.assertEqual(frame.getAntwortErrorCode(), 0x00)

    def test_decode_antwortFrame_ok_2(self):
        data = getAnwortFrame(error_code=0x00, interface_ok=True, frame_type_ok=True)

        frame = self.gsv6.decode_antwort_frame(data)

        self.assertEqual(frame.getLength(), 0)
        self.assertEqual(frame.getAntwortErrorCode(), 0x00)

    def test_decode_antwortFrame_fail_1(self):
        payload = bytearray([0x33, 0x44])
        payloadLength = len(payload)
        data = getAnwortFrame(payload, error_code=0x00, interface_ok=False, frame_type_ok=True)

        with self.assertRaises(GSV6_Communication_Error) as context:
            frame = self.gsv6.decode_antwort_frame(data)

    def test_decode_antwortFrame_fail_2(self):
        payload = bytearray([0x33, 0x44])
        payloadLength = len(payload)
        data = getAnwortFrame(payload, error_code=0x00, interface_ok=True, frame_type_ok=False)

        with self.assertRaises(GSV6_Communication_Error) as context:
            frame = self.gsv6.decode_antwort_frame(data)

    def test_decode_antwortFrame_fail_3(self):
        # unkown ErroCode
        data = getAnwortFrame(error_code=0x19, interface_ok=True, frame_type_ok=True)

        with self.assertRaises(GSV6_ReturnError_Exception) as context:
            frame = self.gsv6.decode_antwort_frame(data)

    def test_decode_messwertFrame_ok(self):
        data = getMesswertFrame(messwerte=True, interface_ok=True, frame_type_ok=True)

        frame = self.gsv6.decode_messwert_frame(data)

        self.assertEqual(frame.getMesswertDataTypeAsString(), 'int16')
        self.assertEqual(frame.getChannelCount(), 1)

    def test_decode_messwertFrame_fail_1(self):
        data = getMesswertFrame(messwerte=True, interface_ok=False, frame_type_ok=True)

        with self.assertRaises(GSV6_Communication_Error) as context:
            frame = self.gsv6.decode_messwert_frame(data)

    def test_decode_messwertFrame_fail_2(self):
        data = getMesswertFrame(messwerte=True, interface_ok=True, frame_type_ok=False)

        with self.assertRaises(GSV6_Communication_Error) as context:
            frame = self.gsv6.decode_messwert_frame(data)

    def test_decode_messwertFrame_fail_3(self):
        data = getMesswertFrame(messwerte=False, interface_ok=True, frame_type_ok=True)

        with self.assertRaises(GSV6_Communication_Error) as context:
            frame = self.gsv6.decode_messwert_frame(data)

    def test_buildGetInterface(self):
        data = self.gsv6.buildGetInterface()

        self.assertEqual(data, bytearray([0xaa, 0x91, 0x01, 0x00, 0x85]))

    def test_buildReadZero(self):
        data = self.gsv6.buildReadZero(1)

        self.assertEqual(data, bytearray([0xaa, 0x91, 0x02, 0x01, 0x85]))

    def test_buildWriteZero(self):
        data = self.gsv6.buildWriteZero(1, self.gsv6.convertFloatsToBytes([1.0]))

        self.assertEqual(data, bytearray([0xaa, 0x95, 0x03, 0x01, 0x3f, 0x80, 0x00, 0x00, 0x85]))

    def test_buildReadInputType(self):
        data = self.gsv6.buildReadInputType(1)

        self.assertEqual(data, bytearray([0xaa, 0x92, 0xa2, 0x01, 0x00, 0x85]))

    def test_buildWriteInputType(self):
        # 4mV/V = 400
        inputType_data = self.gsv6.convertIntToBytes(400)

        data = self.gsv6.buildWriteInputType(1, 0x00, inputType_data)

        self.assertEqual(data, bytearray([0xaa, 0x96, 0x34, 0x00, 0x00, 0x00, 0x00, 0x01, 0x90, 0x85]))

    def test_cache(self):
        self.assertFalse(self.gsv6.isConfigCached('FirmwareVersion', 'major'))

        self.gsv6.addConfigToCache('FirmwareVersion', 'major', 1)

        self.assertTrue(self.gsv6.isConfigCached('FirmwareVersion', 'major'))

        self.gsv6.markChachedConfiAsDirty('FirmwareVersion', 'major')

        self.assertFalse(self.gsv6.isConfigCached('FirmwareVersion', 'major'))

if __name__ == '__main__':
    unittest.main()
