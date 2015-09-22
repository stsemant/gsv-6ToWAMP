'''
Created on 31.08.2015

@author: Dennis Rump
'''
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
