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

from datetime import datetime

print datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
print datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
import csv
fileWritingStarted=False
fileName='test.csv'
#fileName = datetime.utcnow().strftime('%Y-%m-%d %H-%M-%S')
with open('./messungen/'+fileName, 'ab') as csvfile:
    fieldnames = ['timestamp', 'channel0', 'channel1', 'channel2', 'channel3', 'channel4', 'channel5']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

    writer.writeheader()
    writer.writerow({'timestamp': '2015-10-05 13:00:05.544', 'channel3': -3.2044434192357585e-05, 'channel2': 0.00016022217459976673, 'channel1': 3.2044434192357585e-05, 'channel0': 6.408886838471517e-05, 'channel5': 0.0002563554735388607, 'channel4': 6.408886838471517e-05})
    writer.writerow({'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], 'channel0': 3.23})
    writer.writerow({'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], 'channel0': 3.23})
    writer.writerow({'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], 'channel0': 3.23})
