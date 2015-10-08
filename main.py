# -*- coding: utf-8 -*-
__author__ = 'dennis rump'

import gsv6_sim
import gsv6_seriall_lib
from collections import deque
gsv6_sim = gsv6_sim.GSV6_sim()
gsv6 = gsv6_seriall_lib.GSV6_seriall_lib()


# Ringbuffer
class RingBuffer:
    # source: http://www.programmieraufgaben.ch/aufgabe/ringpuffer-mit-arrays/yui8z5du
    def __init__(self, size):
        self.maxsize = size
        self.data = []
        self.size = 0

    def append(self, x):
        self.data.append(x)
        if self.size < self.maxsize:
            self.size = self.size + 1
        else:
            self.data.pop(0)

    def get(self):
        if self.size > 0:
            self.size = self.size -1
            return self.data.pop(0)

    def get_buffer(self):
        return self.data

    def get_size(self):
        return self.size
'''
r = RingBuffer(4)
r.append(bytearray([0x99,0xAA,0xBB]))
r.append(bytearray([0x33,0x44,0x55]))
r.append(bytearray([0x66,0x77,0x88]))
print('Payload: ' + ' '.join(format(z, '02x') for z in r.get()))
'''
x =  deque([])
x.append(bytearray([0x99,0xAA,0xBB]))
x.append(bytearray([0x33,0x44,0x55]))
x.append(bytearray([0x66,0x77,0x88]))
y = x.popleft()
print('Payload: ' + ' '.join(format(z, '02x') for z in y))

a = [1,2]
b = a
a = []
print(a)
print(b)

a = [1,2]
b = a
del a[:]
print(a)
print(b)

payload = bytearray([0x33,0x66,0x77])
result = gsv6_sim.getAnwortFrame(payload)
result = gsv6.stripSerialPreAndSuffix(result)
result = gsv6.decode_antwort_frame(result)

print('Laenge des Payloads ' + str(result.getLength()))
print('Payload: ' + ' '.join(format(x, '02x') for x in result.getPayload()))
'''
print('Laenge des Payloads ' + str(frame.getLength()))
print('Payload: ' + ' '.join(format(x, '02x') for x in frame.getPayload()))
'''
config = {}
config['xyz'] = "test"
config['a'] = []
config['a'].append("r")
testobj = 'asd'

if config.has_key(testobj):
    print("ja1")

testobj = 'xyz'
if config.has_key(testobj):
    print("ja2")

config.pop(testobj, None)

if config.has_key(testobj):
    print("ja3")
