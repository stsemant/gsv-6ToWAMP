# -*- coding: utf-8 -*-
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
class GSV6_sim:

    def getMesswertFrame(self):
        #0xAA        # Serial start
        #0b00        # Messwert Frame
        #0b01        # Interface -> Serial
        #0b0000      # Anzahl der Kanaele -> 5 -> 1001
        #0b10010000  # Steuerbyte / Statusbyte indikato <7>=1 <6:4>=001 (int16) <3:0>=0 (kein Error)
        #481         # Data    -> da int 16 zwei byte -> 0x00 0x01
        #0x85        # Serial ende

        # => 0xAA 0001 0001 1001 0000  0x00 0x01 0x85
        # => 0xAA    0x11      0x90    0x00 0x01 0x85

        result = bytearray([0xAA,0x11,0x90,0x00,0x01,0x85])
        return result

    def getAnwortFrame(self, data={}, error_code=0x00):
        #0xAA        # Serial start
        #0b01        # Anwort Frame
        #0b01        # Interface -> Serial
        #0b0000      # Payload Length
        #0b00000000  # Steuerbyte / Statusbyte indikato <7>=1 <6:4>=001 (int16) <3:0>=0 (kein Error)
        #481         # Data    -> da int 16 zwei byte -> 0x00 0x01
        #0x85        # Serial ende

        # => 0xAA 0101 xxxx  1001 0000 x 0x85
        # => 0xAA    0x5?      0x50    x 0x85

        payload = bytearray(data)
        length = int(len(payload))
        secondByte = 0x50 | length

        result = bytearray([0xAA,secondByte,error_code])
        result.extend(payload)
        result.append(0x85)
        return result
