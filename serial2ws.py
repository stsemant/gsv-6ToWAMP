# -*- coding: utf-8 -*-
###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Tavendo GmbH
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
###############################################################################

from twisted.internet.defer import inlineCallbacks
from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import LineReceiver
from twisted.protocols.basic import protocol

from autobahn.twisted.wamp import ApplicationSession
from autobahn.wamp.types import CallDetails
from collections import deque

import error_codes
import GSV6_BasicFrameType
# import Queue
from Queue import Queue, Empty
import unit_codes
from autobahn.wamp.types import RegisterOptions

spezialOptions = RegisterOptions(details_arg="details")

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 'format': '
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# formatter = logging.Formatter('[%(levelname)s] %(message)s [%(module)s %(funcName)s %(lineno)d]')
# logger.setFormatter(formatter)


# config
maxCacheMessCount = 1000

import datetime
class GSV_6Protocol(protocol.Protocol):
    inDataBuffer = {}
    trace = False

    def connectionLost(self, reason):
        self.session.lostSerialConnection(reason.getErrorMessage())

    def __init__(self, session, frameQueue, anfrageQueue, debug=False):
        self.debug = debug
        self.session = session
        self.inDataBuffer = bytearray()
        self.frameQueue = frameQueue
        self.anfrageQueue = anfrageQueue

    def dataReceived(self, data):
        self.inDataBuffer.extend(data)
        # logger.debug('[' + __name__ + '] serial data received.')
        # print('[serial|data received] ' + ' '.join(format(x, '02x') for x in bytearray(data)))

        self.checkForCompleteFrame()
        # print("get DATA")

    def checkForCompleteFrame(self, recursion=-1):
        state = 0
        counter = 0
        frametype = 0
        payloadLength = 0
        foundcompleteframe = False
        tempArray = bytearray()

        # drop all bytes to find sync byte
        while (len(self.inDataBuffer) > 0) and (self.inDataBuffer[0] != 0xAA):
            self.inDataBuffer.pop(0)
            if self.trace:
                print('Drop Byte.')

        # min length messwert = 5 Byte
        # min length antwort  = 4 Byte
        # abort if not enougth data received
        if len(self.inDataBuffer) < 4:
            if self.trace:
                print('return, because minimal FrameLength not reached.')
            return

        for b in self.inDataBuffer:
            tempArray.append(b)
            counter += 1
            if self.trace:
                print('State: ' + str(state))

            if state == 0:
                # okay we strip sync bytes 0xAA and 0x85 in this function
                # strip 0xAA in state 0
                del tempArray[-1]

                # next state
                state = 1
            elif state == 1:
                # check FrameType, Interface and length/channels -> state=2
                # if AntwortFrame or MessFrame?
                if not (((b & 0xC0) == 0x40) or ((b & 0xC0) == 0x00)):
                    # in this scope we can't pop (del) first byte -> idea: blank the 0xAA
                    self.inDataBuffer[0] = 0x00
                    if self.debug:
                        print('[break] Frame seems to be not a Antwort or MsessFrame.')
                    break
                else:
                    frametype = int(b >> 6)
                # if Interface== Serial?
                if not (b & 0x30 == 0x10):
                    # in this scope we can't pop (del) first byte -> idea: blank the 0xAA
                    self.inDataBuffer[0] = 0x00
                    if self.debug:
                        print('[break] Interface != Serial')
                    break
                # payloadLength for AntwortFrame or count of Channels for Messframe
                payloadLength = int(b & 0x0F)
                if self.trace:
                    print('payloadLength=' + str(payloadLength))
                state = 2
                # if not -> drop: state=0;counter=0;drop incommingDataBuffer.pop(0), tempArray=[]
            elif state == 2:
                # check status byte Mess=indicator; AntwortFrame = in listErrorList?; payloadLength=calculate legnth of expected payload -> state=3
                if frametype == 0:
                    if self.trace:
                        print('detected MessFrame')
                    # it's a MessFrame
                    # first check Indikator==1
                    if (b & 0x80) != 0x80:
                        # in this scope we can't pop (del) first byte -> idea: blank the 0xAA
                        self.inDataBuffer[0] = 0x00
                        if self.debug:
                            print('[break] Indikator!=1')
                        break
                    # now get datatype as multiplier for payloadLength
                    multiplier = int((b & 0x70) >> 4) + 1
                    if self.trace:
                        print('multiplier: ' + str(multiplier))
                    # start count at 0-> +1
                    payloadLength += 1
                    payloadLength *= multiplier
                    if self.trace:
                        print('payloadLength: ' + str(payloadLength))
                    state = 3
                elif frametype == 1:
                    if self.trace:
                        print('detected Antwort Frame')
                    # it's a AntwortFrame
                    # check if errorcode is in the list
                    if not error_codes.error_code_to_error_shortcut.has_key(b):
                        # in this scope we can't pop (del) first byte -> idea: blank the 0xAA
                        self.inDataBuffer[0] = 0x00
                        if self.debug:
                            print("[break] can't find errorcode ins list.")
                        break
                    else:
                        # if no payload there, stepover state3
                        if payloadLength > 0:
                            state = 3
                        else:
                            state = 4
                else:
                    # any other frametype is not allow: drop
                    # in this scope we can't pop (del) first byte -> idea: blank the 0xAA
                    self.inDataBuffer[0] = 0x00
                    if self.debug:
                        print('[break] other FrameType detected.')
                    break
                    # if not -> drop: state=0;counter=0;drop incommingDataBuffer.pop(0), tempArray=[]
                    # if payload>6*4Byte, drop also
            elif state == 3:
                if self.trace:
                    print('counter-state: ' + str((counter - state)))
                if payloadLength == (counter - state):
                    state = 4
                    # so we got the whole payload goto state=4
            elif state == 4:
                # at the first time in state 4, we have to break
                # if b== 0x85 -> we have a complete Frame; pushback the complete Frame and remove copyed bytes from incommingBuffer and break For-Loop
                if not (b == 0x85):
                    # in this scope we can't pop (del) first byte -> idea: blank the 0xAA
                    self.inDataBuffer[0] = 0x00
                    if self.trace:
                        print("[break] can't find 0x85")
                else:
                    if self.trace:
                        print('[break] found an complete Frame')
                    foundcompleteframe = True

                    # okay we strip sync bytes 0xAA and 0x85 in this function
                    # strip 0x85 in state 4
                    del tempArray[-1]

                    # pushback data here!
                    # publish WAMP event to all subscribers on topic
                    ##
                    frame = GSV6_BasicFrameType.BasicFrame(tempArray)
                    # self.frameQueue.append(frame)
                    try:
                        # put() is blocking, put_nowait() ist non-blocking
                        # self.frameQueue.put(frame)
                        self.frameQueue.put_nowait(frame)
                    except Queue.Full:
                        self.session.addError('a complete Frame was droped, because Queue was full')
                        if self.debug:
                            print('a complete Frame was droped, because Queue was full')
                    # self.session.publish(u"com.myapp.mcu.on_frame_received",
                    #                     str(''.join(format(x, '02x') for x in bytearray(tempArray))))
                    if self.trace:
                        print(
                            '[serial] Received compelte Frame: ' + ' '.join(
                                format(x, '02x') for x in bytearray(tempArray)))

                # break anyway
                break
                # else drop last <counter> bytes and retry sync

        if foundcompleteframe:
            # remove copyed items
            self.inDataBuffer[0:counter - 1] = []
            if self.trace:
                print('new inDataBuffer[0]: ' + ' '.join(format(self.inDataBuffer[0], '02x')))

        # at this point we have to test, if we have enougth data for a second frame
        # execute this function again if (recursion == -1 and len(incommingBuffer>4) or ()
        lenthOfData = len(self.inDataBuffer)
        if (lenthOfData > 3) and (recursion != lenthOfData):
            if self.trace:
                print('[rec] start rec')
            self.checkForCompleteFrame(lenthOfData)
        else:
            if self.trace:
                print('[rec] no more rec')

    def write(self, data):
        self.transport.write(data)


import os.path
import csv
import threading


class CSVwriter(threading.Thread):
    def __init__(self, startTimeStampStr, dictListOfMessungen, csvList_lock, path='./messungen/', debug=False):
        threading.Thread.__init__(self)
        self.startTimeStampStr = startTimeStampStr
        self.path = path
        self.filenName = self.path + self.startTimeStampStr + '.csv'
        self.dictListOfMessungen = dictListOfMessungen
        self.csvList_lock = csvList_lock
        self.debug = debug

    def run(self):
        if not os.path.exists(self.filenName):
            self.writeHeader = True
        else:
            self.writeHeader = False

        with open(self.filenName, 'ab') as csvfile:
            fieldnames = ['timestamp', 'channel0', 'channel1', 'channel2', 'channel3', 'channel4', 'channel5']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

            if self.writeHeader:
                writer.writeheader()
            self.csvList_lock.acquire()
            writer.writerows(self.dictListOfMessungen)
            del self.dictListOfMessungen[:]
            self.csvList_lock.release()


class MessFrameHandler():
    def __init__(self, session, gsv_lib, eventHandler):
        self.session = session
        self.gsv_lib = gsv_lib
        self.eventHandler = eventHandler
        self.messCounter = 0
        self.startTimeStampStr = ''
        self.hasTOWriteCSV = False

    def computeFrame(self, frame):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        payload = bytearray(frame.getPayload())
        values = self.gsv_lib.convertToFloat(payload)

        payload = {}
        counter = 0
        for f in values:
            # there is no append/add function for Python Dictionaries
            payload[u'channel' + str(counter) + '_value'] = f
            counter += 1
        if frame.isMesswertInputOverload():
            inputOverload = True
        else:
            inputOverload = False
        if frame.isMesswertSixAchsisError():
            sixAchisError = True
        else:
            sixAchisError = False

        if self.hasTOWriteCSV:
            # handle CSVwrting
            self.messCounter += 1
            # add data here
            self.session.messCSVDictList_lock.acquire()

            self.session.messCSVDictList.append(
                {'timestamp': timestamp, 'channel0': values[0], 'channel1': values[1], 'channel2': values[2],
                 'channel3': values[3], 'channel4': values[4], 'channel5': values[5]})
            self.session.messCSVDictList_lock.release()
            if (self.messCounter >= maxCacheMessCount):
                self.messCounter = 0
                # semaphore lock?
                self.writeCSVdataNow()

        # publish WAMP event to all subscribers on topic
        self.session.publish(u"de.me_systeme.gsv.onMesswertReceived", [payload, inputOverload, sixAchisError])

    def setStartTimeStamp(self, startTimeStampStr, hasToWriteCSV):
        self.startTimeStampStr = startTimeStampStr
        self.hasTOWriteCSV = hasToWriteCSV

    def writeCSVdataNow(self, startTimeStampStr=''):
        CSVwriter(self.startTimeStampStr, self.session.messCSVDictList, self.session.messCSVDictList_lock,
                  self.session.config.extra['csvpath']).run()

import collections
class AntwortFrameHandler():
    # thread-safe? nothing to do here -> queue-Object is an thread-safe

    def __init__(self, session, gsv_lib, eventHandler, queue):
        self.session = session
        self.gsv_lib = gsv_lib
        self.eventHandler = eventHandler
        self.queue = queue

    def computeFrame(self, frame):
        func_name_for_error = ""
        try:
            if not self.queue.empty():
                function_informations = self.queue.get_nowait()
                methodNameToCall, args = function_informations.popitem()
                func_name_for_error = methodNameToCall
                methodToCall = getattr(self, methodNameToCall)
                if args is not None:
                    result = methodToCall(frame, args)
                else:
                    result = methodToCall(frame)
        except Exception, e:
            msg = 'Unexpected error[antwort][' + func_name_for_error + ']:' + str(e)
            self.session.addError(msg)
            print(msg)

    def rcvStartStopTransmission(self, frame, start):
        self.session.publish(u"de.me_systeme.gsv.onStartStopTransmission", [frame.getAntwortErrorCode(), start])

    def rcvGetUnitText(self, frame):
        if not (frame.getPayload()[0] == 0):
            print('error')
        else:
            text = self.gsv_lib.convertToString(frame.getPayload()[1:])[0]
            self.session.publish(u"de.me_systeme.gsv.onGetUnitText", [frame.getAntwortErrorCode(), text])

    def rcvSetUnitText(self, frame):
        self.session.publish(u"de.me_systeme.gsv.onSetUnitText", frame.getAntwortErrorCode())

    def rcvGetGetInterface(self, frame, ubertragung=None):
        reuslt = self.gsv_lib.decodeGetInterface(frame.getPayload())
        self.session.publish(u"de.me_systeme.gsv.onGetInterface", reuslt)

    def rcvGetReadAoutScale(self, frame, channelNo):
        values = self.gsv_lib.convertToFloat(frame.getPayload())
        self.session.publish(u"de.me_systeme.gsv.onGetReadAoutScale",
                             [frame.getAntwortErrorCode(), channelNo, values[0]])

    def rcvWriteAoutScale(self, frame, channelNo):
        self.session.publish(u"de.me_systeme.gsv.onWriteAoutScale",
                             [frame.getAntwortErrorCode(), channelNo])

    def rcvGetReadZero(self, frame, channelNo):
        values = self.gsv_lib.convertToFloat(frame.getPayload())
        self.session.publish(u"de.me_systeme.gsv.onGetReadZero",
                             [frame.getAntwortErrorCode(), channelNo, values[0]])

    def rcvWriteZero(self, frame, channelNo):
        self.session.publish(u"de.me_systeme.gsv.onWriteZero",
                             [frame.getAntwortErrorCode(), channelNo])

    def rcvGetReadUserScale(self, frame, channelNo):
        values = self.gsv_lib.convertToFloat(frame.getPayload())
        self.session.publish(u"de.me_systeme.gsv.onGetReadUserScale",
                             [frame.getAntwortErrorCode(), channelNo, values[0]])

    def rcvWriteUserScale(self, frame, channelNo):
        self.session.publish(u"de.me_systeme.gsv.onWriteUserScale",
                             [frame.getAntwortErrorCode(), channelNo])

    def rcvGetUnitNoAsText(self, frame, channelNo):
        unit_str = unit_codes.unit_code_to_shortcut.get(frame.getPayload()[0])
        self.session.publish(u"de.me_systeme.gsv.onGetUnitNoAsText",
                             [frame.getAntwortErrorCode(), channelNo, unit_str, frame.getAntwortErrorText()])

    def rcvGetUnitNo(self, frame, channelNo):
        # unit_str = unit_codes.unit_code_to_shortcut.get(frame.getPayload()[0])
        # self.session.publish(u"de.me_systeme.gsv.onGetUnitNo", [frame.getAntwortErrorCode(), channelNo, unit_str, frame.getAntwortErrorText()])
        unit_str = unit_codes.unit_code_to_shortcut.get(frame.getPayload()[0])
        unit_str = unit_str.decode("utf8")
        self.session.publish(u"de.me_systeme.gsv.onGetUnitNo",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo,
                              frame.getPayload()[0], unit_str])

    def rcvWriteUnitNo(self, frame, channelNo):
        self.session.publish(u"de.me_systeme.gsv.onWriteUnitNo",
                             [frame.getAntwortErrorCode(), channelNo, frame.getAntwortErrorText()])

    def rcvGetSerialNo(self, frame):
        serialNo = self.gsv_lib.convertToUint32_t(frame.getPayload())[0]
        self.session.publish(u"de.me_systeme.gsv.onGetSerialNo",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), serialNo])

    def rcvGetDeviceHours(self, frame):
        if frame.getAntwortErrorCode() == 0:
            deviceHours = self.gsv_lib.convertToFloat(frame.getPayload())
            self.session.publish(u"de.me_systeme.gsv.onGetDeviceHours",
                                 [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), deviceHours[0]])
        else:
            self.session.publish(u"de.me_systeme.gsv.onGetDeviceHours",
                                 [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), -1])

    def rcvGetDataRate(self, frame):
        dataRate = self.gsv_lib.convertToFloat(frame.getPayload())[0]
        self.session.publish(u"de.me_systeme.gsv.onGetDataRate",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), dataRate])

    def rcvWriteDataRate(self, frame, dataRateValue):
        self.session.publish(u"de.me_systeme.gsv.onWriteDataRate",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), dataRateValue])

    def rcvWriteSaveAll(self, frame):
        self.session.publish(u"de.me_systeme.gsv.onWriteSaveAll",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText()])

    def rcvWriteSetZero(self, frame, channelNo):
        self.session.publish(u"de.me_systeme.gsv.onWriteSetZero",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo])

    def rcvGetFirmwareVersion(self, frame):
        versionCodes = self.gsv_lib.convertToUint16_t(frame.getPayload())
        if isinstance(versionCodes, collections.Sequence) and len(versionCodes) >1:
            self.session.publish(u"de.me_systeme.gsv.onGetFirmwareVersion",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), versionCodes])
        else:
            self.session.publish(u"de.me_systeme.gsv.onGetFirmwareVersion",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), -1])
            
    def rcvGetReadUserOffset(self, frame, channelNo):
        values = self.gsv_lib.convertToFloat(frame.getPayload())
        self.session.publish(u"de.me_systeme.gsv.onGetReadUserOffset",
                             [frame.getAntwortErrorCode(), channelNo, values[0]])

    def rcvWriteUserOffset(self, frame, channelNo):
        self.session.publish(u"de.me_systeme.gsv.onWriteUserOffset",
                             [frame.getAntwortErrorCode(), channelNo])

    def rcvGetReadInputType(self, frame, channelNo):
        values = self.gsv_lib.convertToUint32_t(frame.getPayload())
        self.session.publish(u"de.me_systeme.gsv.onGetReadInputType",
                             [frame.getAntwortErrorCode(), channelNo, values[0]])

from datetime import datetime

import glob
import os
class GSVeventHandler():
    # here we register all "wamp" functions and all "wamp" listners around GSV-6CPU-Modul
    def __init__(self, session, gsv_lib, antwortQueue, eventHandler):
        self.session = session
        self.gsv_lib = gsv_lib
        self.antwortQueue = antwortQueue
        self.eventHandler = eventHandler
        # start register
        self.regCalls()

    def regCalls(self):
        print('register...')
        self.session.register(self.startStopTransmisson, u"de.me_systeme.gsv.startStopTransmission", spezialOptions)
        self.session.register(self.getUnitText, u"de.me_systeme.gsv.getUnitText")
        self.session.register(self.setUnitText, u"de.me_systeme.gsv.setUnitText")
        self.session.register(self.getGetInterface, u"de.me_systeme.gsv.getGetIntetface")
        self.session.register(self.getReadAoutScale, u"de.me_systeme.gsv.getReadAoutScale")
        self.session.register(self.writeAoutScale, u"de.me_systeme.gsv.WriteAoutScale")
        self.session.register(self.getReadZero, u"de.me_systeme.gsv.getReadZero")
        self.session.register(self.writeZero, u"de.me_systeme.gsv.WriteZero")
        self.session.register(self.getReadUserScale, u"de.me_systeme.gsv.getReadUserScale")
        self.session.register(self.writeUserScale, u"de.me_systeme.gsv.WriteUserScale")
        self.session.register(self.getUnitNoAsText, u"de.me_systeme.gsv.getUnitNoAsText")
        self.session.register(self.getUnitNo, u"de.me_systeme.gsv.getUnitNo")
        self.session.register(self.writeUnitNo, u"de.me_systeme.gsv.WriteUnitNo")
        self.session.register(self.getSerialNo, u"de.me_systeme.gsv.getSerialNo")
        self.session.register(self.resetAntwortQueue, u"de.me_systeme.gsv.resetAntwortQueue")
        self.session.register(self.getDeviceHours, u"de.me_systeme.gsv.getDeviceHours")
        self.session.register(self.getDataRate, u"de.me_systeme.gsv.getDataRate")
        self.session.register(self.writeDataRate, u"de.me_systeme.gsv.WriteDataRate")
        self.session.register(self.writeSaveAll, u"de.me_systeme.gsv.WriteSaveAll")
        self.session.register(self.writeSetZero, u"de.me_systeme.gsv.WriteSetZero")
        self.session.register(self.getCSVFileList, u"de.me_systeme.gsv.getCSVFileList")
        self.session.register(self.deleteCSVFile, u"de.me_systeme.gsv.deleteCSVFile")
        self.session.register(self.getFirmwareVersion, u"de.me_systeme.gsv.getFirmwareVersion")
        self.session.register(self.getReadUserOffset, u"de.me_systeme.gsv.getReadUserOffset")
        self.session.register(self.writeUserOffset, u"de.me_systeme.gsv.WriteUserOffset")
        self.session.register(self.getReadInputType, u"de.me_systeme.gsv.getReadInputType")

    def startStopTransmisson(self, start, hasToWriteCSVdata=False, **kwargs):
        if start:
            print('Start Transmission. Call from ' + str(kwargs['details'].caller))
            data = self.gsv_lib.buildStartTransmission()
            self.eventHandler.setStartTimeStampStr(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), hasToWriteCSVdata)
        else:
            print('Stops Transmission. Call from ' + str(kwargs['details'].caller))
            data = self.gsv_lib.buildStopTransmission()
            self.eventHandler.writeCSVdata()
        self.session.writeAntwort(data, 'rcvStartStopTransmission', start)

    def getUnitText(self):
        self.session.writeAntwort(self.gsv_lib.buildGetUnitText(), 'rcvGetUnitText')

    def setUnitText(self, text):
        self.session.writeAntwort(self.gsv_lib.buildSetUnitText(text), 'rcvSetUnitText')

    def getGetInterface(self, ubertragung=None):
        self.session.writeAntwort(self.gsv_lib.buildGetInterface(ubertragung), 'rcvGetGetInterface', ubertragung)

    def getReadAoutScale(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildReadAoutScale(channelNo), 'rcvGetReadAoutScale', channelNo)

    def writeAoutScale(self, channelNo, AoutScale):
        # first convert float to bytes
        scale = self.gsv_lib.convertFloatsToBytes([AoutScale])
        self.session.writeAntwort(self.gsv_lib.buildWriteAoutScale(channelNo, scale), 'rcvWriteAoutScale', channelNo)

    def getReadZero(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildReadZero(channelNo), 'rcvGetReadZero', channelNo)

    def writeZero(self, channelNo, zeroValue):
        # first convert float to bytes
        zero = self.gsv_lib.convertFloatsToBytes([zeroValue])
        self.session.writeAntwort(self.gsv_lib.buildWriteZero(channelNo, zero), 'rcvWriteZero', channelNo)

    def getReadUserScale(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildReadUserScale(channelNo), 'rcvGetReadUserScale', channelNo)

    def writeUserScale(self, channelNo, userScaleValue):
        # first convert float to bytes
        userScale = self.gsv_lib.convertFloatsToBytes([userScaleValue])
        self.session.writeAntwort(self.gsv_lib.buildWriteUserScale(channelNo, userScale), 'rcvWriteUserScale',
                                  channelNo)

    def getUnitNoAsText(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildGetUnitNo(channelNo), 'rcvGetUnitNoAsText', channelNo)

    def getUnitNo(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildGetUnitNo(channelNo), 'rcvGetUnitNo', channelNo)

    def writeUnitNo(self, channelNo, unitNo):
        self.session.writeAntwort(self.gsv_lib.buildWriteUnitNo(channelNo, unitNo), 'rcvWriteUnitNo', channelNo)

    def getSerialNo(self):
        self.session.writeAntwort(self.gsv_lib.buildGetSerialNo(), 'rcvGetSerialNo')

    def getDeviceHours(self):
        self.session.writeAntwort(self.gsv_lib.buildGetDeviceHours(), 'rcvGetDeviceHours')

    def getDataRate(self):
        self.session.writeAntwort(self.gsv_lib.buildGetDataRate(), 'rcvGetDataRate')

    def writeDataRate(self, dataRateValue):
        dataRate = self.gsv_lib.convertFloatsToBytes([dataRateValue])
        self.session.writeAntwort(self.gsv_lib.buildWriteDataRate(dataRate), 'rcvWriteDataRate', dataRateValue)

    def writeSaveAll(self):
        self.session.writeAntwort(self.gsv_lib.buildWriteSaveAll(), 'rcvWriteSaveAll')

    def writeSetZero(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildWriteSetZero(channelNo), 'rcvWriteSetZero', channelNo)

    def getFirmwareVersion(self):
        self.session.writeAntwort(self.gsv_lib.buildgetFirmwareVersion(), 'rcvGetFirmwareVersion')
        
    def getReadUserOffset(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildReadUserOffset(channelNo), 'rcvGetReadUserOffset', channelNo)

    def writeUserOffset(self, channelNo, userOffsetValue):
        # first convert float to bytes
        userOffset = self.gsv_lib.convertFloatsToBytes([userOffsetValue])
        self.session.writeAntwort(self.gsv_lib.buildWriteUserOffset(channelNo, userOffset), 'rcvWriteUserOffset',
                                  channelNo)
    def getReadInputType(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildReadInputType(channelNo), 'rcvGetReadInputType', channelNo)

    def getCSVFileList(self):
        # in this function, we write nothing to the GSV-modul
        # source: http://stackoverflow.com/questions/168409/how-do-you-get-a-directory-listing-sorted-by-creation-date-in-python
        search_dir = self.session.config.extra['csvpath']
        files = filter(os.path.isfile, glob.glob(search_dir + "*.csv"))
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        print files
        return [search_dir,files]

    def deleteCSVFile(self, fileName):
        filepath = self.session.config.extra['csvpath'] + fileName
        if(os.path.isfile(filepath)):
            try:
                os.remove(filepath)
            except Exception, e:
                msg = '[File I/O error] ' + fileName + ': ' + str(e)
                self.session.addError(msg)
                print(msg)
                return False
            else:
                return True
        else:
            print("Datei konnte nicht gefunden werden (gelöscht werden")
            return False

    # this fuction didnt write to the modul, its resets the antwort Queue
    def resetAntwortQueue(self):
        try:
            while True:
                self.antwortQueue.get_nowait()
        except Empty:
            return True
        except Exception, e:
            msg = 'Unexpected error[resetAntwortQueue]:' + str(e)
            self.session.addError(msg)
            print(msg)
            return False


from gsv6_seriall_lib import GSV6_seriall_lib


class FrameRouter(threading.Thread):
    # lock for running variale, nötig?
    lock = threading.Lock()
    startTimeStampStr = ''
    hasToWriteCSVdata = False

    def __init__(self, session, frameQueue, antwortQueue, debug=False):
        threading.Thread.__init__(self)
        self.debug = debug
        self.session = session
        self.frameQueue = frameQueue
        self.antwortQueue = antwortQueue
        self.running = False

        # GSV-6CPU Lib
        self.gsv6 = GSV6_seriall_lib()
        self.eventHandler = GSVeventHandler(self.session, self.gsv6, antwortQueue, self)
        self.messFrameEventHandler = MessFrameHandler(self.session, self.gsv6, self.eventHandler)
        self.antwortFrameEventHandler = AntwortFrameHandler(self.session, self.gsv6, self.eventHandler,
                                                            self.antwortQueue, )

        # fallback, this flag kills this thread if main thread killed
        self.daemon = True

    def run(self):
        print("[router] start loop.")
        # arbeits Thread: router -> routen von AntwortFrames und MessFrames
        FrameRouter.lock.acquire()
        self.running = True
        FrameRouter.lock.release()
        while self.running:
            try:
                # newFrame = self.frameQueue.popleft()
                newFrame = self.frameQueue.get()
            except IndexError:
                pass
            except Queue.Empty:
                pass
            else:
                if self.debug:
                    pass
                    # print('[router] ' + newFrame.toString())
                if newFrame.getFrameType() == 0:
                    # MesswertFrame
                    self.messFrameEventHandler.computeFrame(newFrame)
                elif newFrame.getFrameType() == 1:
                    # AntwortFrame
                    self.antwortFrameEventHandler.computeFrame(newFrame)
                else:
                    # error
                    print('nothing to do with an FrameType != Messwert/Antwort')

        print("[router] exit loop.")

    def stop(self):
        FrameRouter.lock.acquire()
        self.running = False
        FrameRouter.lock.release()

        # TODO: evtl reduanter aufruf! überprüfen!
        self.writeCSVdata()

    def setStartTimeStampStr(self, str, hasToWriteCSV):
        self.startTimeStampStr = str
        self.hasToWriteCSVdata = hasToWriteCSV
        self.messFrameEventHandler.setStartTimeStamp(str, hasToWriteCSV)

    def writeCSVdata(self):
        if (self.hasToWriteCSVdata):
            self.messFrameEventHandler.writeCSVdataNow(self.startTimeStampStr)

from time import sleep
class McuComponent(ApplicationSession):
    """
    RPi WAMP application component.
    """

    # The Queue-Object is an threadsafe FIFO Buffer.
    # Operations like put and get are atomic
    # this queue holds all incomming complete Frames
    frameInBuffer = Queue(50)

    # this queue holds the ordered config requests
    antwortQueue = Queue(50)

    # what ist deque? = double-ended queue. it's a thread-safe ringbuffer
    # this deque holds the errors as string
    errorQueue = deque([], 20)

    # hier werden die messungen gespeichert
    messCSVDictList = []
    messCSVDictList_lock = threading.Lock()

    # to ensure that we have a thead-safe write function, we need that look
    serialWrite_lock = threading.Lock()

    isSerialConnected = False

    # GSV-6CPU RX bufferoverflow prevention
    actTime = None
    lastTime = datetime.now()

    '''
    def __init__(self):
        # x =  deque([])
        pass
    '''

    # cleanup here
    def leave(self):
        self.router.stop()
        # wait max 1 Sec.
        self.router.join(1.0)

    @inlineCallbacks
    def onJoin(self, details):
        print("MyComponent ready! Configuration: {}".format(self.config.extra))
        port = self.config.extra['port']
        baudrate = self.config.extra['baudrate']
        debug = self.config.extra['debug']

        # first of all, register the getErrors Function
        yield self.register(self.getErrors, u"de.me_systeme.gsv.getErrors")
        yield self.register(self.getIsSerialConnected, u"de.me_systeme.gsv.getIsSerialConnected")

        # create an router object/thread
        self.router = FrameRouter(self, self.frameInBuffer, self.antwortQueue, debug)
        self.router.start()

        # serialProtocol = McuProtocol(self, debug)
        serialProtocol = GSV_6Protocol(self, self.frameInBuffer, self.antwortQueue, debug)

        print('About to open serial port {0} [{1} baud] ..'.format(port, baudrate))
        try:
            self.serialPort = SerialPort(serialProtocol, port, reactor, baudrate=baudrate)
            self.isSerialConnected = True

            # data = self.gsv_lib.buildStopTransmission()
            # self.session.writeAntwort(data, 'rcvStartStopTransmission', start)

        except Exception as e:
            print('Could not open serial port: {0}'.format(e))
            self.leave()
        else:
            pass

    def __exit__(selfself):
        print('Exit.')

    def __del__(selfself):
        print('del.')

    def getErrors(self):
        return list(self.errorQueue)

    def addError(self, errorString):
        self.errorQueue.append(errorString)
        self.publish(u"de.me_systeme.gsv.onError", errorString)

    sendCounter = 0
    def writeAntwort(self, data, functionName, args=None):
        # okay this function have to be atomic
        # we protect it with a lock!
        self.serialWrite_lock.acquire()
        self.actTime = datetime.now()
        diffTime = self.actTime - self.lastTime
        if diffTime.days<=0 and diffTime.seconds<=2:
            if(diffTime.seconds==0 and diffTime.microseconds<2000):
                self.sendCounter +=1
                if self.sendCounter>=10:
                    self.sendCounter=0
                    print("serialWait, for GSV-6PU RX Buffer overflow")
                    sleep(0.2) # Time in seconds
            else:
                self.sendCounter=0
        try:
            self.antwortQueue.put_nowait({functionName: args})
            self.serialPort.write(str(data))
            print('[MyComp|write] Data: ' + ' '.join(format(z, '02x') for z in data))
            msg = '[MyComp|write] Data: ' + ' '.join(format(z, '02x') for z in data)
            self.addError(msg)
        except NameError:
            if self.debug:
                print('[MyComp] serialport not openend')
        finally:
            self.lastTime = datetime.now()
            self.serialWrite_lock.release()

    '''
    def write(self, data):
        # okay this function have to be atomic
        # we protect it with a lock!
        self.serialWrite_lock.acquire()
        try:
            self.serialPort.write(str(data))
            print('[MyComp|write] Data: ' + ' '.join(format(z, '02x') for z in data))
            str = '[MyComp|write] Data: ' + ' '.join(format(z, '02x') for z in data)
            self.addError(str)
        except NameError:
            if self.debug:
                print('[MyComp] serialport not openend')
        finally:
            self.serialWrite_lock.release()
    '''
    def publish_test(self, topic, args):
        self.publish(topic, args)

    def getIsSerialConnected(self):
        return self.isSerialConnected

    def lostSerialConnection(self, errorMessage):
        print("Lost SerialConnection: " + errorMessage)
        self.addError("[serialConnection:LOST] " + errorMessage)
        # TODO: reconnect?
        self.isSerialConnected = False
        self.publish(u"de.me_systeme.gsv.serialConnectionLost")


if __name__ == '__main__':

    import sys
    import argparse
    from twisted.web.resource import Resource
    # log.setLevel(logging.DEBUG)
    # parse command line arguments
    ##
    parser = argparse.ArgumentParser()

    parser.add_argument("-d", "--debug", action="store_true",
                        help="Enable debug output.")

    parser.add_argument("--baudrate", type=int, default=115200,
                        choices=[300, 1200, 2400, 4800, 9600, 19200, 57600, 115200],
                        help='Serial port baudrate.')

    if sys.platform == 'win32':
        parser.add_argument("--port", type=str, default='4',
                            help='Serial port to use (e.g. 3 for a COM port on Windows, /dev/ttyATH0 for Arduino Yun, /dev/ttyACM0 for Serial-over-USB on RaspberryPi.')
    else:
        parser.add_argument("--port", type=str, default='/dev/ttyAMA0',
                            help='Serial port to use (e.g. 3 for a COM port on Windows, /dev/ttyATH0 for Arduino Yun, /dev/ttyACM0 for Serial-over-USB on RaspberryPi.')

    parser.add_argument("--web", type=int, default=8000,
                        help='Web port to use for embedded Web server. Use 0 to disable.')

    parser.add_argument("--router", type=str, default=None,
                        help='If given, connect to this WAMP router. Else run an embedded router on 8080.')

    parser.add_argument("--csvpath", type=str, default='./messungen/',
                        help='If given, the CSV-Files will be saved there.')

    args = parser.parse_args()

    if args.csvpath[-1] != '/':
        args.csvpath += '/'
    if not os.path.exists(args.csvpath):
        print('invalid CSV Path')
        exit()

    try:
        # on Windows, we need port to be an integer
        args.port = int(args.port)
    except ValueError:
        pass

    from twisted.python import log as logTwisted

    logTwisted.startLogging(sys.stdout)

    # import Twisted reactor
    ##
    if sys.platform == 'win32':
        # on windows, we need to use the following reactor for serial support
        # http://twistedmatrix.com/trac/ticket/3802
        ##
        from twisted.internet import win32eventreactor

        win32eventreactor.install()

    from twisted.internet import reactor

    print("Using Twisted reactor {0}".format(reactor.__class__))

    # create embedded web server for static files
    ##
    if args.web:
        from twisted.web.server import Site
        from twisted.web.static import File

        #reactor.listenTCP(args.web, Site(File(".")))
        # wwwroot
        root = File(".")
        # messungenroot
        root.putChild("messungen", File(args.csvpath))
        reactor.listenTCP(args.web, Site(root))

    # run WAMP application component
    ##
    from autobahn.twisted.wamp import ApplicationRunner

    router = args.router or u'ws://127.0.0.1:8080/ws/'

    runner = ApplicationRunner(router, u"me_gsv6",
                               extra={'port': args.port, 'baudrate': args.baudrate, 'csvpath': args.csvpath,
                                      'debug': True})
    # extra={'port': args.port, 'baudrate': args.baudrate, 'debug': args.debug})

    # start the component and the Twisted reactor ..
    ##
    runner.run(McuComponent)
