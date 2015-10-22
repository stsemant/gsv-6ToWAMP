# -*- coding: utf-8 -*-
from LoggingWAMP_Handler import WAMP_Handler

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
# und der zugehÃ¶rigen Dokumentationen (die "Software") erhÃ¤lt, die
# Erlaubnis erteilt, uneingeschrÃ¤nkt zu benutzen, inklusive und ohne
# Ausnahme, dem Recht, sie zu verwenden, kopieren, Ã¤ndern, fusionieren,
# verlegen, verbreiten, unter-lizenzieren und/oder zu verkaufen, und
# Personen, die diese Software erhalten, diese Rechte zu geben, unter
# den folgenden Bedingungen:
#
# Der obige Urheberrechtsvermerk und dieser Erlaubnisvermerk sind in
# alle Kopien oder Teilkopien der Software beizulegen.
#
# DIE SOFTWARE WIRD OHNE JEDE AUSDRÃœCKLICHE ODER IMPLIZIERTE GARANTIE
# BEREITGESTELLT, EINSCHLIESSLICH DER GARANTIE ZUR BENUTZUNG FÃœR DEN
# VORGESEHENEN ODER EINEM BESTIMMTEN ZWECK SOWIE JEGLICHER
# RECHTSVERLETZUNG, JEDOCH NICHT DARAUF BESCHRÃ„NKT. IN KEINEM FALL SIND
# DIE AUTOREN ODER COPYRIGHTINHABER FÃœR JEGLICHEN SCHADEN ODER SONSTIGE
# ANSPRUCH HAFTBAR ZU MACHEN, OB INFOLGE DER ERFÃœLLUNG VON EINEM
# VERTRAG, EINEM DELIKT ODER ANDERS IM ZUSAMMENHANG MIT DER BENUTZUNG
# ODER SONSTIGE VERWENDUNG DER SOFTWARE ENTSTANDEN.
#
###############################################################################
#
# Based on WebSocket/WAMP Serial2ws Example (https://github.com/tavendo/AutobahnPython/tree/master/examples/twisted/wamp/app/serial2ws)
# Dependencies:
#   Autobahn    http://autobahn.ws/         (MIT License)
#   Bootstrap   http://getbootstrap.com/    (MIT License)
#   jQuery      https://jquery.com/         (MIT License)
#   Smoothie    http://smoothiecharts.org/  (MIT License)
#   Highcharts  http://www.highcharts.com/  (Do you want to use Highcharts for a personal or non-profit project? Then you can use Highchcarts for free under the  Creative Commons Attribution-NonCommercial 3.0 License
#
###############################################################################
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError

from twisted.internet.error import ConnectionRefusedError, TCPTimedOutError, ReactorAlreadyInstalledError, \
    CannotListenError
from twisted.internet.defer import inlineCallbacks
from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import protocol

import logging
import logging.handlers
from twisted.python import log

TRACE = 5
logging.addLevelName(TRACE, 'TRACE')


def trace(self, message, *args, **kws):
    self.log(TRACE, message, *args, **kws)


logging.Logger.trace = trace
logging.basicConfig()
# FileSize in MB
maxLogFileSize=1

from autobahn.twisted.wamp import ApplicationSession
from collections import deque

import error_codes
import GSV6_BasicFrameType
# import Queue
from Queue import Queue, Empty
import unit_codes
from autobahn.wamp.types import RegisterOptions

spezialOptions = RegisterOptions(details_arg="details")


# 'format': '
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# formatter = logging.Formatter('[%(levelname)s] %(message)s [%(module)s %(funcName)s %(lineno)d]')
# logger.setFormatter(formatter)


# config
maxCacheMessCount = 1000

import datetime


class GSV_6Protocol(protocol.Protocol):
    inDataBuffer = {}

    def connectionLost(self, reason):
        self.session.lostSerialConnection(reason.getErrorMessage())

    def __init__(self, session, frameQueue, anfrageQueue):
        self.session = session
        self.inDataBuffer = bytearray()
        self.frameQueue = frameQueue
        self.anfrageQueue = anfrageQueue

    def dataReceived(self, data):
        self.inDataBuffer.extend(data)
        logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace(
            'data received: ' + ' '.join(format(x, '02x') for x in bytearray(data)))

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
            logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('Drop Byte.')

        # min length messwert = 5 Byte
        # min length antwort  = 4 Byte
        # abort if not enougth data received
        if len(self.inDataBuffer) < 4:
            logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace(
                'return, because minimal FrameLength not reached.')
            return

        for b in self.inDataBuffer:
            tempArray.append(b)
            counter += 1
            logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('State: ' + str(state))

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
                    logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace(
                        '[break] Frame seems to be not a Antwort or MsessFrame.')
                    break
                else:
                    frametype = int(b >> 6)
                # if Interface== Serial?
                if not (b & 0x30 == 0x10):
                    # in this scope we can't pop (del) first byte -> idea: blank the 0xAA
                    self.inDataBuffer[0] = 0x00
                    logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('[break] Interface != Serial')
                    break
                # payloadLength for AntwortFrame or count of Channels for Messframe
                payloadLength = int(b & 0x0F)
                logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('payloadLength=' + str(payloadLength))
                state = 2
                # if not -> drop: state=0;counter=0;drop incommingDataBuffer.pop(0), tempArray=[]
            elif state == 2:
                # check status byte Mess=indicator; AntwortFrame = in listErrorList?; payloadLength=calculate legnth of expected payload -> state=3
                if frametype == 0:
                    logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('detected MessFrame')
                    # it's a MessFrame
                    # first check Indikator==1
                    if (b & 0x80) != 0x80:
                        # in this scope we can't pop (del) first byte -> idea: blank the 0xAA
                        self.inDataBuffer[0] = 0x00
                        logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('[break] Indikator!=1')
                        break
                    # now get datatype as multiplier for payloadLength
                    multiplier = int((b & 0x70) >> 4) + 1
                    logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('multiplier: ' + str(multiplier))
                    # start count at 0-> +1
                    payloadLength += 1
                    payloadLength *= multiplier
                    logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('payloadLength: ' + str(payloadLength))
                    state = 3
                elif frametype == 1:
                    logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('detected Antwort Frame')
                    # it's a AntwortFrame
                    # check if errorcode is in the list
                    if not error_codes.error_code_to_error_shortcut.has_key(b):
                        # in this scope we can't pop (del) first byte -> idea: blank the 0xAA
                        self.inDataBuffer[0] = 0x00
                        logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace(
                            "[break] can't find errorcode ins list.")
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
                    logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('[break] other FrameType detected.')
                    break
                    # if not -> drop: state=0;counter=0;drop incommingDataBuffer.pop(0), tempArray=[]
                    # if payload>6*4Byte, drop also
            elif state == 3:
                logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('counter-state: ' + str((counter - state)))
                if payloadLength == (counter - state):
                    state = 4
                    # so we got the whole payload goto state=4
            elif state == 4:
                # at the first time in state 4, we have to break
                # if b== 0x85 -> we have a complete Frame; pushback the complete Frame and remove copyed bytes from incommingBuffer and break For-Loop
                if not (b == 0x85):
                    # in this scope we can't pop (del) first byte -> idea: blank the 0xAA
                    self.inDataBuffer[0] = 0x00
                    logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace("[break] can't find 0x85")
                else:
                    logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('[break] found an complete Frame')
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
                        logging.getLogger('serial2ws.MyComp.GSV_6Protocol').warning(
                            'a complete Frame was droped, because Queue was full')
                    # self.session.publish(u"com.myapp.mcu.on_frame_received",
                    #                     str(''.join(format(x, '02x') for x in bytearray(tempArray))))
                    logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace(
                        '[serial] Received compelte Frame: ' + ' '.join(format(x, '02x') for x in bytearray(tempArray)))

                # break anyway
                break
                # else drop last <counter> bytes and retry sync

        if foundcompleteframe:
            # remove copyed items
            self.inDataBuffer[0:counter - 1] = []
            logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace(
                'new inDataBuffer[0]: ' + ' '.join(format(self.inDataBuffer[0], '02x')))

        # at this point we have to test, if we have enougth data for a second frame
        # execute this function again if (recursion == -1 and len(incommingBuffer>4) or ()
        lenthOfData = len(self.inDataBuffer)
        if (lenthOfData > 3) and (recursion != lenthOfData):
            logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('[rec] start rec')
            self.checkForCompleteFrame(lenthOfData)
        else:
            logging.getLogger('serial2ws.MyComp.GSV_6Protocol').trace('[rec] no more rec')

    def write(self, data):
        self.transport.write(data)


import csv
import threading


class CSVwriter(threading.Thread):
    def __init__(self, startTimeStampStr, dictListOfMessungen, csvList_lock, units, path='./messungen/'):
        threading.Thread.__init__(self)
        self.startTimeStampStr = startTimeStampStr
        self.path = path
        self.filenName = self.path + self.startTimeStampStr + '.csv'
        self.dictListOfMessungen = dictListOfMessungen
        self.csvList_lock = csvList_lock
        self.units = units

    def run(self):
        if not os.path.exists(self.filenName):
            self.writeHeader = True
        else:
            self.writeHeader = False

        with open(self.filenName, 'ab') as csvfile:
            fieldnames = ['timestamp', 'channel0', 'channel1', 'channel2', 'channel3', 'channel4', 'channel5']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            if self.writeHeader:
                headernames = {'timestamp': 'timestamp', 'channel0': 'channel0[' + self.units[0] + ']',
                               'channel1': 'channel1[' + self.units[1] + ']',
                               'channel2': 'channel2[' + self.units[2] + ']',
                               'channel3': 'channel3[' + self.units[3] + ']',
                               'channel4': 'channel4[' + self.units[4] + ']',
                               'channel5': 'channel5[' + self.units[5] + ']'}
                writer.writerow(headernames)

            self.csvList_lock.acquire()
            writer.writerows(self.dictListOfMessungen)
            del self.dictListOfMessungen[:]
            self.csvList_lock.release()
            logging.getLogger('serial2ws.MyComp.router.MessFrameHandler.CSVwriter').trace('CSV-File written')


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
        logging.getLogger('serial2ws.MyComp.router.MessFrameHandler').trace('Received MessFrame: published.')

    def setStartTimeStamp(self, startTimeStampStr, hasToWriteCSV):
        self.startTimeStampStr = startTimeStampStr
        self.hasTOWriteCSV = hasToWriteCSV

    def writeCSVdataNow(self, startTimeStampStr=''):
        # build unit index
        units = []
        if self.gsv_lib.isConfigCached('UnitNo', 1):
            units.append(unit_codes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 1)))
        else:
            units.append('undefined')
        if self.gsv_lib.isConfigCached('UnitNo', 2):
            units.append(unit_codes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 2)))
        else:
            units.append('undefined')
        if self.gsv_lib.isConfigCached('UnitNo', 3):
            units.append(unit_codes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 3)))
        else:
            units.append('undefined')
        if self.gsv_lib.isConfigCached('UnitNo', 4):
            units.append(unit_codes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 4)))
        else:
            units.append('undefined')
        if self.gsv_lib.isConfigCached('UnitNo', 5):
            units.append(unit_codes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 5)))
        else:
            units.append('undefined')
        if self.gsv_lib.isConfigCached('UnitNo', 6):
            units.append(unit_codes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 6)))
        else:
            units.append('undefined')

        # start csvWriter
        writer = CSVwriter(self.startTimeStampStr, self.session.messCSVDictList, self.session.messCSVDictList_lock,
                           units,
                           self.session.config.extra['csvpath'])
        writer.start()


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
            logging.getLogger('serial2ws.MyComp.router.AntwortFrameHandler').critical(msg)

    def rcvStartStopTransmission(self, frame, start):
        self.session.publish(u"de.me_systeme.gsv.onStartStopTransmission",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), start])

    def rcvGetUnitText(self, frame, slot):
        # datatype-conversion
        text = self.gsv_lib.convertToString(frame.getPayload()[1:])[0]
        text = text.decode("ascii")
        text = text.decode("utf8")
        # for cache
        self.gsv_lib.addConfigToCache('UnitText', slot, text)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onGetUnitText",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), slot, text])

    def rcvSetUnitText(self, frame, slot):
        # for cache
        if frame.getAntwortErrorCode() == 0:
            # TODO: Slot 0 und 1 beachten! -> nicht impl.
            self.gsv_lib.markChachedConfiAsDirty('UnitText', slot)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onSetUnitText",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), slot])

    def rcvGetGetInterface(self, frame, ubertragung=None):
        # datatype-conversion
        result = self.gsv_lib.decodeGetInterface(frame.getPayload())
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onGetInterface",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), result])

    def rcvGetReadAoutScale(self, frame, channelNo):
        # datatype-conversion
        value = self.gsv_lib.convertToFloat(frame.getPayload())[0]
        # for cache
        self.gsv_lib.addConfigToCache('AoutScale', channelNo, value)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onGetReadAoutScale",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo, value])

    def rcvWriteAoutScale(self, frame, channelNo):
        # for cache
        if frame.getAntwortErrorCode() == 0:
            self.gsv_lib.markChachedConfiAsDirty('AoutScale', channelNo)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onWriteAoutScale",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo])

    def rcvGetReadZero(self, frame, channelNo):
        # datatype-conversion
        value = self.gsv_lib.convertToFloat(frame.getPayload())[0]
        # for cache
        self.gsv_lib.addConfigToCache('Zero', channelNo, value)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onGetReadZero",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo, value])

    def rcvWriteZero(self, frame, channelNo):
        # for cache
        if frame.getAntwortErrorCode() == 0:
            self.gsv_lib.markChachedConfiAsDirty('Zero', channelNo)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onWriteZero",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo])

    def rcvGetReadUserScale(self, frame, channelNo):
        # datatype-conversion
        value = self.gsv_lib.convertToFloat(frame.getPayload())[0]
        # for cache
        self.gsv_lib.addConfigToCache('UserScale', channelNo, value)
        # answer from GSV-6CPU
        values = self.gsv_lib.convertToFloat(frame.getPayload())
        self.session.publish(u"de.me_systeme.gsv.onGetReadUserScale",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo, value])

    def rcvWriteUserScale(self, frame, channelNo):
        # for cache
        if frame.getAntwortErrorCode() == 0:
            self.gsv_lib.markChachedConfiAsDirty('UserScale', channelNo)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onWriteUserScale",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo])

    # TODO: this function is obsoate. !remove!
    def rcvGetUnitNoAsText(self, frame, channelNo):
        unit_str = unit_codes.unit_code_to_shortcut.get(frame.getPayload()[0])
        self.session.publish(u"de.me_systeme.gsv.onGetUnitNoAsText",
                             [frame.getAntwortErrorCode(), channelNo, unit_str, frame.getAntwortErrorText()])

    def rcvGetUnitNo(self, frame, channelNo):
        # datatype-conversion
        unit_str = unit_codes.unit_code_to_shortcut.get(frame.getPayload()[0])
        unit_str = unit_str.decode("utf8")
        # for cache
        self.gsv_lib.addConfigToCache('UnitNo', channelNo, frame.getPayload()[0])
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onGetUnitNo",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo,
                              frame.getPayload()[0], unit_str])

    def rcvWriteUnitNo(self, frame, channelNo):
        # for cache
        if frame.getAntwortErrorCode() == 0:
            self.gsv_lib.markChachedConfiAsDirty('UnitNo', channelNo)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onWriteUnitNo",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo])

    def rcvGetSerialNo(self, frame):
        # datatype-conversion
        serialNo = self.gsv_lib.convertToUint32_t(frame.getPayload())[0]
        # for cache
        self.gsv_lib.addConfigToCache('SerialNo', 'SerialNo', serialNo)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onGetSerialNo",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), serialNo])

    def rcvGetDeviceHours(self, frame):
        # his property is not suitable for caching
        # answer from GSV-6CPU
        if frame.getAntwortErrorCode() == 0:
            deviceHours = self.gsv_lib.convertToFloat(frame.getPayload())
            self.session.publish(u"de.me_systeme.gsv.onGetDeviceHours",
                                 [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), deviceHours[0]])
        else:
            self.session.publish(u"de.me_systeme.gsv.onGetDeviceHours",
                                 [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), -1])

    def rcvGetDataRate(self, frame):
        # datatype-conversion
        dataRate = self.gsv_lib.convertToFloat(frame.getPayload())[0]
        # for cache
        self.gsv_lib.addConfigToCache('DataRate', 'DataRate', dataRate)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onGetDataRate",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), dataRate])

    def rcvWriteDataRate(self, frame, dataRateValue):
        # for cache
        if frame.getAntwortErrorCode() == 0:
            self.gsv_lib.markChachedConfiAsDirty('DataRate', 'DataRate')
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onWriteDataRate",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), dataRateValue])

    def rcvWriteSaveAll(self, frame):
        self.session.publish(u"de.me_systeme.gsv.onWriteSaveAll",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText()])

    def rcvWriteSetZero(self, frame, channelNo):
        self.session.publish(u"de.me_systeme.gsv.onWriteSetZero",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo])

    def rcvGetFirmwareVersion(self, frame):
        # datatype-conversion
        versionCodes = self.gsv_lib.convertToUint16_t(frame.getPayload())
        # answer from GSV-6CPU
        if isinstance(versionCodes, collections.Sequence) and len(versionCodes) > 1:
            # for cache
            self.gsv_lib.addConfigToCache('FirmwareVersion', 'major', versionCodes[0])
            self.gsv_lib.addConfigToCache('FirmwareVersion', 'minor', versionCodes[1])
            self.session.publish(u"de.me_systeme.gsv.onGetFirmwareVersion",
                                 [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), versionCodes])
        else:
            self.gsv_lib.addConfigToCache('FirmwareVersion', -1)
            self.session.publish(u"de.me_systeme.gsv.onGetFirmwareVersion",
                                 [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), -1])

    def rcvGetReadUserOffset(self, frame, channelNo):
        # datatype-conversion
        values = self.gsv_lib.convertToFloat(frame.getPayload())
        # for cache
        self.gsv_lib.addConfigToCache('UserOffset', channelNo, values[0])
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onGetReadUserOffset",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo, values[0]])

    def rcvWriteUserOffset(self, frame, channelNo):
        # for cache
        if frame.getAntwortErrorCode() == 0:
            self.gsv_lib.markChachedConfiAsDirty('UserOffset', channelNo)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onWriteUserOffset",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo])

    def rcvGetReadInputType(self, frame, channelNo):
        value = self.gsv_lib.convertToUint32_t(frame.getPayload())[0]
        # for cache
        self.gsv_lib.addConfigToCache('InputType', channelNo, value)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onGetReadInputType",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo, value])

    def rcvWriteInputType(self, frame, channelNo):
        # for cache
        if frame.getAntwortErrorCode() == 0:
            self.gsv_lib.markChachedConfiAsDirty('InputType', channelNo)
        # answer from GSV-6CPU
        self.session.publish(u"de.me_systeme.gsv.onWriteInputType",
                             [frame.getAntwortErrorCode(), frame.getAntwortErrorText(), channelNo])

    def rcvSetMEid(self, frame, minor):
        logging.getLogger('serial2ws.MyComp.router.AntwortFrameHandler').info('cache ready.')
        self.session.sys_ready = True
        if frame.getAntwortErrorCode() == 0:
            self.gsv_lib.addConfigToCache('ME_ID', 'ME_ID', True)
            logging.getLogger('serial2ws.MyComp.router.AntwortFrameHandler').info('ME ID has been set successfully.')
        else:
            self.gsv_lib.addConfigToCache('ME_ID', 'ME_ID', False)
            logging.getLogger('serial2ws.MyComp.router.AntwortFrameHandler').info("ME ID could not be set.")


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
        # print('register...')
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
        self.session.register(self.writeInputType, u"de.me_systeme.gsv.WriteInputType")
        self.session.register(self.getCachedConfig, u"de.me_systeme.gsv.getCachedConfig")
        self.session.register(self.setDateTimeFromBrowser, u"de.me_systeme.gsv.setDateTimeFromBrowser")
        self.session.register(self.isSystemReady, u"de.me_systeme.gsv.isSystemReady")
        self.session.register(self.rebootSystem, u"de.me_systeme.gsv.rebootSystem")
        self.session.register(self.getLogFileList, u"de.me_systeme.gsv.getLogFileList")

    def startStopTransmisson(self, start, hasToWriteCSVdata=False, **kwargs):
        if start:
            msg = 'Start Transmission. Call from ' + str(kwargs['details'].caller)
            logging.getLogger('serial2ws.MyComp.router.GSVeventHandler').info(msg)
            data = self.gsv_lib.buildStartTransmission()
            self.eventHandler.setStartTimeStampStr(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), hasToWriteCSVdata)
        else:
            msg = 'Stop Transmission. Call from ' + str(kwargs['details'].caller)
            logging.getLogger('serial2ws.MyComp.router.GSVeventHandler').info(msg)
            data = self.gsv_lib.buildStopTransmission()
            self.eventHandler.writeCSVdata()
        self.session.writeAntwort(data, 'rcvStartStopTransmission', start)

    def getUnitText(self, slot=0):
        if self.gsv_lib.isConfigCached('UnitText', slot):
            self.session.publish(u"de.me_systeme.gsv.onGetUnitText",
                                 [0x00, 'ERR_OK', slot, self.gsv_lib.getCachedProperty('UnitText', slot)])
        else:
            self.session.writeAntwort(self.gsv_lib.buildGetUnitText(slot), 'rcvGetUnitText', slot)

    def setUnitText(self, text, slot=0):
        self.session.writeAntwort(self.gsv_lib.buildSetUnitText(text, slot), 'rcvSetUnitText', slot)

    def getGetInterface(self, ubertragung=None):
        # this property is not suitable for caching
        self.session.writeAntwort(self.gsv_lib.buildGetInterface(ubertragung), 'rcvGetGetInterface', ubertragung)

    def getReadAoutScale(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildReadAoutScale(channelNo), 'rcvGetReadAoutScale', channelNo)

    def writeAoutScale(self, channelNo, AoutScale):
        # first convert float to bytes
        scale = self.gsv_lib.convertFloatsToBytes([AoutScale])
        self.session.writeAntwort(self.gsv_lib.buildWriteAoutScale(channelNo, scale), 'rcvWriteAoutScale', channelNo)

    def getReadZero(self, channelNo):
        if self.gsv_lib.isConfigCached('Zero', channelNo):
            self.session.publish(u"de.me_systeme.gsv.onGetReadZero",
                                 [0x00, 'ERR_OK', channelNo, self.gsv_lib.getCachedProperty('Zero', channelNo)])
        else:
            self.session.writeAntwort(self.gsv_lib.buildReadZero(channelNo), 'rcvGetReadZero', channelNo)

    def writeZero(self, channelNo, zeroValue):
        # first convert float to bytes
        zero = self.gsv_lib.convertFloatsToBytes([zeroValue])
        self.session.writeAntwort(self.gsv_lib.buildWriteZero(channelNo, zero), 'rcvWriteZero', channelNo)

    def getReadUserScale(self, channelNo):
        if self.gsv_lib.isConfigCached('UserScale', channelNo):
            self.session.publish(u"de.me_systeme.gsv.onGetReadUserScale",
                                 [0x00, 'ERR_OK', channelNo, self.gsv_lib.getCachedProperty('UserScale', channelNo)])
        else:
            self.session.writeAntwort(self.gsv_lib.buildReadUserScale(channelNo), 'rcvGetReadUserScale', channelNo)

    def writeUserScale(self, channelNo, userScaleValue):
        # first convert float to bytes
        userScale = self.gsv_lib.convertFloatsToBytes([userScaleValue])
        self.session.writeAntwort(self.gsv_lib.buildWriteUserScale(channelNo, userScale), 'rcvWriteUserScale',
                                  channelNo)

    def getUnitNoAsText(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildGetUnitNo(channelNo), 'rcvGetUnitNoAsText', channelNo)

    def getUnitNo(self, channelNo):
        if self.gsv_lib.isConfigCached('UnitNo', channelNo):
            unitNo = self.gsv_lib.getCachedProperty('UnitNo', channelNo)
            unit_str = unit_codes.unit_code_to_shortcut.get(unitNo)
            unit_str = unit_str.decode("utf8")
            self.session.publish(u"de.me_systeme.gsv.onGetUnitNo",
                                 [0x00, 'ERR_OK', channelNo, unitNo, unit_str])
        else:
            self.session.writeAntwort(self.gsv_lib.buildGetUnitNo(channelNo), 'rcvGetUnitNo', channelNo)

    def writeUnitNo(self, channelNo, unitNo):
        self.session.writeAntwort(self.gsv_lib.buildWriteUnitNo(channelNo, unitNo), 'rcvWriteUnitNo', channelNo)

    def getSerialNo(self):
        if self.gsv_lib.isConfigCached('SerialNo', 'SerialNo'):
            self.session.publish(u"de.me_systeme.gsv.onGetSerialNo",
                                 [0x00, 'ERR_OK', self.gsv_lib.getCachedProperty('SerialNo', 'SerialNo')])
        else:
            self.session.writeAntwort(self.gsv_lib.buildGetSerialNo(), 'rcvGetSerialNo')

    def getDeviceHours(self):
        self.session.writeAntwort(self.gsv_lib.buildGetDeviceHours(), 'rcvGetDeviceHours')

    def getDataRate(self):
        if self.gsv_lib.isConfigCached('DataRate', 'DataRate'):
            self.session.publish(u"de.me_systeme.gsv.onGetDataRate",
                                 [0x00, 'ERR_OK', self.gsv_lib.getCachedProperty('DataRate', 'DataRate')])
        else:
            self.session.writeAntwort(self.gsv_lib.buildGetDataRate(), 'rcvGetDataRate')

    def writeDataRate(self, dataRateValue):
        dataRate = self.gsv_lib.convertFloatsToBytes([dataRateValue])
        self.session.writeAntwort(self.gsv_lib.buildWriteDataRate(dataRate), 'rcvWriteDataRate', dataRateValue)

    def writeSaveAll(self):
        self.session.writeAntwort(self.gsv_lib.buildWriteSaveAll(), 'rcvWriteSaveAll')

    def writeSetZero(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildWriteSetZero(channelNo), 'rcvWriteSetZero', channelNo)

    def getFirmwareVersion(self):
        if self.gsv_lib.isConfigCached('FirmwareVersion', 'major'):
            self.session.publish(u"de.me_systeme.gsv.onGetFirmwareVersion",
                                 [0x00, 'ERR_OK', [self.gsv_lib.getCachedProperty('FirmwareVersion', 'major'),
                                                   self.gsv_lib.getCachedProperty('FirmwareVersion', 'minor')]])
        else:
            self.session.writeAntwort(self.gsv_lib.buildgetFirmwareVersion(), 'rcvGetFirmwareVersion')

    def getReadUserOffset(self, channelNo):
        if self.gsv_lib.isConfigCached('UserOffset', channelNo):
            self.session.publish(u"de.me_systeme.gsv.onGetReadUserOffset",
                                 [0x00, 'ERR_OK', channelNo, self.gsv_lib.getCachedProperty('UserOffset', channelNo)])
        else:
            self.session.writeAntwort(self.gsv_lib.buildReadUserOffset(channelNo), 'rcvGetReadUserOffset', channelNo)

    def writeUserOffset(self, channelNo, userOffsetValue):
        # first convert float to bytes
        userOffset = self.gsv_lib.convertFloatsToBytes([userOffsetValue])
        self.session.writeAntwort(self.gsv_lib.buildWriteUserOffset(channelNo, userOffset), 'rcvWriteUserOffset',
                                  channelNo)

    def getReadInputType(self, channelNo):
        if self.gsv_lib.isConfigCached('InputType', channelNo):
            self.session.publish(u"de.me_systeme.gsv.onGetReadInputType",
                                 [0x00, 'ERR_OK', channelNo, self.gsv_lib.getCachedProperty('InputType', channelNo)])
        else:
            self.session.writeAntwort(self.gsv_lib.buildReadInputType(channelNo), 'rcvGetReadInputType', channelNo)

    def writeInputType(self, channelNo, inputTypeValue):
        # first convert int to Uint32 and remove leading byte
        inputType = self.gsv_lib.convertIntToBytes(inputTypeValue)[1:]
        # SensIndex is always 0x00 (GSV-6)
        sensIndex = 0x00
        self.session.writeAntwort(self.gsv_lib.buildWriteInputType(channelNo, sensIndex, inputType),
                                  'rcvWriteInputType',
                                  channelNo)

    def getCachedConfig(self):
        return self.gsv_lib.getCachedConfig()

    def setDateTimeFromBrowser(self, dateTimeStr):
        if sys.platform == 'win32':
            return [0x01, "Windows not supported"]
        else:
            x = os.system("sudo date -u -s \"%s\"" % (dateTimeStr))
            if x == 0:
                return [0, "ERR_OK", dateTimeStr]
            else:
                return [x, "an error occurred"]

    def rebootSystem(self):
        if sys.platform == 'win32':
            return [0x01, "Windows not supported"]
        else:
            x = os.system("sudo reboot")
            if x == 0:
                return [0, "ERR_OK"]
            else:
                return [x, "an error occurred"]

    def isSystemReady(self):
        return self.session.sys_ready

    def getCSVFileList(self):
        # in this function, we write nothing to the GSV-modul
        # source: http://stackoverflow.com/questions/168409/how-do-you-get-a-directory-listing-sorted-by-creation-date-in-python
        search_dir = self.session.config.extra['csvpath']
        files = filter(os.path.isfile, glob.glob(search_dir + "*.csv"))
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return [search_dir, files]

    def getLogFileList(self):
        # in this function, we write nothing to the GSV-modul
        search_dir = "./logs/"
        files = filter(os.path.isfile, glob.glob(search_dir + "*.*"))
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return [search_dir, files]

    def deleteCSVFile(self, fileName):
        filepath = self.session.config.extra['csvpath'] + fileName
        if (os.path.isfile(filepath)):
            try:
                os.remove(filepath)
            except Exception, e:
                msg = '[File I/O error] ' + fileName + ': ' + str(e)
                logging.getLogger('serial2ws.MyComp.router.GSVeventHandler').critical(msg)
                return False
            else:
                return True
        else:
            msg = fileName + ' konnte nicht gefunden werden (gelÃ¶scht werden)'
            logging.getLogger('serial2ws.MyComp.GSV_6Protocol').warning(msg)
            return False

    # this fuction didnt write to the modul, its resets the antwort Queue
    def resetAntwortQueue(self):
        try:
            while True:
                self.antwortQueue.get_nowait()
        except Empty:
            return True
        except Exception, e:
            msg = 'resetAntwortQueue Unexpected error: ' + str(e)
            logging.getLogger('serial2ws.MyComp.router.GSVeventHandler').critical(msg)
            return False


class ThreadingWaitForFirmwareVersion(threading.Thread):
    def __init__(self, session, gsv_lib):
        threading.Thread.__init__(self)
        self.session = session
        self.gsv_lib = gsv_lib

    def run(self):
        for x in range(0, 10):
            if self.gsv_lib.isConfigCached('FirmwareVersion', 'minor'):
                minor = self.gsv_lib.getCachedProperty('FirmwareVersion', 'minor')
                minor = int(minor)
                self.gsv_lib.buildSetMEid(minor)
                self.session.writeAntwort(self.gsv_lib.buildSetMEid(minor), 'rcvSetMEid', minor)
                break
            else:
                if x > 1:
                    logging.getLogger('serial2ws.MyComp.router.ThreadingWaitForFirmwareVersion').critical(
                        "wait for cache...; after 10 retrys, please restart application.")
                else:
                    logging.getLogger('serial2ws.MyComp.router.ThreadingWaitForFirmwareVersion').info(
                        "wait for cache...")
                sleep(0.5)


from gsv6_seriall_lib import GSV6_seriall_lib


class FrameRouter(threading.Thread):
    # lock for running variale, nÃ¶tig?
    lock = threading.Lock()
    startTimeStampStr = ''
    hasToWriteCSVdata = False

    def __init__(self, session, frameQueue, antwortQueue):
        threading.Thread.__init__(self)
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

        self.waitFirmwareVersionThread = ThreadingWaitForFirmwareVersion(self.session, self.gsv6)
        # fallback, this flag kills this thread if main thread killed
        self.daemon = True

    def run(self):
        # arbeits Thread: router -> routen von AntwortFrames und MessFrames
        FrameRouter.lock.acquire()
        self.running = True
        FrameRouter.lock.release()
        logging.getLogger('serial2ws.MyComp.router').info('started')

        # now wait for GSV-6CPU
        while not self.session.isSerialConnected and self.running:
            pass
        self.checkForGSVavailableAndFillCache()

        # enter rooter loop
        while self.running:
            try:
                # newFrame = self.frameQueue.popleft()
                newFrame = self.frameQueue.get()
            except IndexError:
                pass
            except Queue.Empty:
                pass
            else:
                logging.getLogger('serial2ws.MyComp.router').trace('new Frame: ' + newFrame.toString())
                if newFrame.getFrameType() == 0:
                    # MesswertFrame
                    self.messFrameEventHandler.computeFrame(newFrame)
                elif newFrame.getFrameType() == 1:
                    # AntwortFrame
                    self.antwortFrameEventHandler.computeFrame(newFrame)
                else:
                    # error
                    logging.getLogger('serial2ws.MyComp.router').debug(
                        'nothing to do with an FrameType != Messwert/Antwort')

        logging.getLogger('serial2ws.MyComp.router').info('exit')

    def stop(self):
        FrameRouter.lock.acquire()
        self.running = False
        FrameRouter.lock.release()

        # TODO: evtl reduanter aufruf! Ã¼berprÃ¼fen!
        self.writeCSVdata()

    def setStartTimeStampStr(self, str, hasToWriteCSV):
        self.startTimeStampStr = str
        self.hasToWriteCSVdata = hasToWriteCSV
        self.messFrameEventHandler.setStartTimeStamp(str, hasToWriteCSV)

    def writeCSVdata(self):
        if (self.hasToWriteCSVdata):
            self.messFrameEventHandler.writeCSVdataNow(self.startTimeStampStr)

    def checkForGSVavailableAndFillCache(self):
        data = self.gsv6.buildStopTransmission()
        while True:
            logging.getLogger('serial2ws.MyComp.router').info('try to reach GSV-6CPU ...')

            self.session.write(data)
            sleep(1.0)
            if not self.frameQueue.empty():
                frame = self.frameQueue.get()
                if frame.getAntwortErrorCode() != 0x00:
                    logging.getLogger('serial2ws.MyComp.router').critical('error init modul-communication. re-try...')

                    self.frameQueue.queue.clear()
                    sleep(1.0)
                else:
                    logging.getLogger('serial2ws.MyComp.router').info('GSV-6CPU found.')
		    self.frameQueue.queue.clear()
                    # fill cache
                    self.eventHandler.getDataRate()
                    self.eventHandler.getReadInputType(1)
                    self.eventHandler.getReadInputType(2)
                    self.eventHandler.getReadInputType(3)
                    self.eventHandler.getReadInputType(4)
                    self.eventHandler.getReadInputType(5)
                    self.eventHandler.getReadInputType(6)
                    self.eventHandler.getReadUserOffset(1)
                    self.eventHandler.getReadUserOffset(2)
                    self.eventHandler.getReadUserOffset(3)
                    self.eventHandler.getReadUserOffset(4)
                    self.eventHandler.getReadUserOffset(5)
                    self.eventHandler.getReadUserOffset(6)
                    self.eventHandler.getReadUserScale(1)
                    self.eventHandler.getReadUserScale(2)
                    self.eventHandler.getReadUserScale(3)
                    self.eventHandler.getReadUserScale(4)
                    self.eventHandler.getReadUserScale(5)
                    self.eventHandler.getReadUserScale(6)
                    self.eventHandler.getUnitNo(1)
                    self.eventHandler.getUnitNo(2)
                    self.eventHandler.getUnitNo(3)
                    self.eventHandler.getUnitNo(4)
                    self.eventHandler.getUnitNo(5)
                    self.eventHandler.getUnitNo(6)
                    self.eventHandler.getUnitText(0)
                    self.eventHandler.getUnitText(1)

                    # getFirmwareVersion() have to bee the last one
                    self.eventHandler.getFirmwareVersion()
                    self.waitFirmwareVersionThread.start()
                    break;
            else:
                msg = "GSV-6CPU didn't answer, will wait 5 sec. and try again..."
                logging.getLogger('serial2ws.MyComp.router').info(msg)
                sleep(5.0)


from time import sleep
import signal


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
    logQueue = deque([], 200)

    # hier werden die messungen gespeichert
    messCSVDictList = []
    messCSVDictList_lock = threading.Lock()

    # to ensure that we have a thead-safe write function, we need that look
    serialWrite_lock = threading.Lock()

    isSerialConnected = False

    # GSV-6CPU RX bufferoverflow prevention
    actTime = None
    lastTime = datetime.now()

    # ready falg
    sys_ready = False

    # cleanup here
    def onLeave(self, details):
        try:
            self.serialPort.reactor.stop()
        except Exception:
            pass
        if self.router.isAlive():
            self.router.stop()
            # wait max 1 Sec.
            self.router.join(1.0)
        logging._removeHandlerRef(self.toWAMP_logger)


    @inlineCallbacks
    def onJoin(self, details):
        port = self.config.extra['port']
        baudrate = self.config.extra['baudrate']

        # install signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.toWAMP_logger  = WAMP_Handler(self, self.logQueue)
        logging.getLogger('serial2ws.MyComp').addHandler(self.toWAMP_logger)

        # first of all, register the getErrors Function
        yield self.register(self.getLog, u"de.me_systeme.gsv.getLog")
        yield self.register(self.getIsSerialConnected, u"de.me_systeme.gsv.getIsSerialConnected")

        # create an router object/thread
        self.router = FrameRouter(self, self.frameInBuffer, self.antwortQueue)


        serialProtocol = GSV_6Protocol(self, self.frameInBuffer, self.antwortQueue)

        logging.getLogger('serial2ws.MyComp').debug(
            'About to open serial port {0} [{1} baud] ..'.format(port, baudrate))
        try:
            self.serialPort = SerialPort(serialProtocol, port, reactor, baudrate=baudrate)
            self.isSerialConnected = True
        except Exception as e:
            logging.getLogger('serial2ws.MyComp').critical('Could not open serial port: {0}. exit!'.format(e))
            os.kill(os.getpid(), signal.SIGTERM)
        else:
            self.router.start()

    def __exit__(self):
        logging.getLogger('serial2ws.MyComp').trace('Exit.')

    def __del__(self):
        logging.getLogger('serial2ws.MyComp').trace('del.')

    def getLog(self):
        return list(self.logQueue)

    sendCounter = 0

    def writeAntwort(self, data, functionName, args=None):
        # okay this function have to be atomic
        # we protect it with a lock!
        self.serialWrite_lock.acquire()
        self.actTime = datetime.now()
        diffTime = self.actTime - self.lastTime
        if diffTime.days <= 0 and diffTime.seconds <= 2:
            if (diffTime.seconds == 0 and diffTime.microseconds < 4000):
                self.sendCounter += 1
                if self.sendCounter >= 8:
                    self.sendCounter = 0
                    logging.getLogger('serial2ws.MyComp').debug("serialWait, prevent GSV-6CPU RX Buffer overflow")
                    sleep(0.2)  # Time in seconds
            else:
                self.sendCounter = 0
        try:
            self.antwortQueue.put_nowait({functionName: args})
            self.serialPort.write(str(data))
            logging.getLogger('serial2ws.MyComp').debug(
                '[serialWrite] Data: ' + ' '.join(format(z, '02x') for z in data))
        except NameError:
            logging.getLogger('serial2ws.MyComp').debug('[MyComp] serialport not openend')
        finally:
            self.lastTime = datetime.now()
            self.serialWrite_lock.release()

    def write(self, data):
        # okay this function have to be atomic
        # we protect it with a lock!
        self.serialWrite_lock.acquire()
        try:
            self.serialPort.write(str(data))
            logging.getLogger('serial2ws.MyComp').debug(
                '[serialWrite] Data: ' + ' '.join(format(z, '02x') for z in data))
        except NameError:
            logging.getLogger('serial2ws.MyComp').debug('serialport not openend')
        finally:
            self.serialWrite_lock.release()

    def publish_test(self, topic, args):
        self.publish(topic, args)

    def getIsSerialConnected(self):
        return self.isSerialConnected

    def lostSerialConnection(self, errorMessage):
        logging.getLogger('serial2ws.MyComp').critical("Lost SerialConnection: " + errorMessage)
        # TODO: reconnect?
        self.isSerialConnected = False
        self.publish(u"de.me_systeme.gsv.serialConnectionLost")

    def signal_handler(self, signal, frame):
        self.disconnect()
        self.leave()


from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet import reactor

if __name__ == '__main__':
    import sys
    import argparse

    if not os.path.exists("./logs"):
        os.makedirs("./logs")

    # init logging
    main_logger = logging.getLogger('serial2ws')
    log_file_handler = logging.handlers.RotatingFileHandler('./logs/app.log', maxBytes=1024 * 1024 * maxLogFileSize, backupCount=4)
    formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s - %(message)s')
    log_file_handler.setFormatter(logging.Formatter('%(asctime)s [%(name)s] %(levelname)s - %(message)s'))
    main_logger.addHandler(log_file_handler)
    stdout_log = logging.StreamHandler()
    # stdout_log.setLevel(logging.DEBUG)
    stdout_log.setFormatter(formatter)
    main_logger.setLevel(logging.DEBUG)

    # create Observer for pipe twisted log to python log
    observer = log.PythonLoggingObserver(loggerName='serial2ws.twisted')
    observer.start()

    # parse command line arguments
    ##
    parser = argparse.ArgumentParser()

    parser.add_argument("-l", "--log", type=str, default='DEBUG',
                        help="set logLevel (CRITICAL, ERROR, WARNING, INFO, DEBUG, TRACE).")

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

    parser.add_argument("--router", type=str, default=u'ws://127.0.0.1:8001/ws/',
                        help='If given, connect to this WAMP router.')

    if sys.platform == 'win32':
        parser.add_argument("--csvpath", type=str, default='./messungen/',
                        help='If given, the CSV-Files will be saved there.')
    else:
        parser.add_argument("--csvpath", type=str, default='/media/usb0/',
                        help='If given, the CSV-Files will be saved there.')

    config = SafeConfigParser()
    config.read(['defaults.conf'])

    # Updateing defaults from config file
    if config.has_section('Defaults'):
        parser.set_defaults(**dict(config.items('Defaults')))

    args = parser.parse_args()

    # CRITICAL, ERROR, WARNING, INFO, DEBUG, TRACE.
    if args.log == 'CRITICAL':
        main_logger.setLevel(logging.CRITICAL)
    elif args.log == 'ERROR':
        main_logger.setLevel(logging.ERROR)
    elif args.log == 'WARNING':
        main_logger.setLevel(logging.WARNING)
    elif args.log == 'INFO':
        main_logger.setLevel(logging.INFO)
    elif args.log == 'DEBUG':
        main_logger.setLevel(logging.DEBUG)
    elif args.log == 'TRACE':
        main_logger.setLevel(5)
    else:
        main_logger.setLevel(logging.DEBUG)
        main_logger.warning('can\'t interprete loglevel, use DEBUG!')

    if args.csvpath[-1] != '/':
        args.csvpath += '/'
    if not os.path.exists(args.csvpath):
        main_logger.critical('invalid CSV Path')
        exit()

    try:
        # on Windows, we need port to be an integer
        args.port = int(args.port)
    except ValueError:
        pass

    # print config
    main_logger.info(
        'Start with config: router {}; Port for Web: {}; Serialport: {}; Baudrate: {}; CSVpath: {}; LogLevel: {}'.format(
            args.router, args.web, args.port, args.baudrate, args.csvpath, args.log))

    # import Twisted reactor
    ##
    if sys.platform == 'win32':
        # on windows, we need to use the following reactor for serial support
        # http://twistedmatrix.com/trac/ticket/3802
        ##
        from twisted.internet import win32eventreactor

        try:
            win32eventreactor.install()
        except ReactorAlreadyInstalledError:
            pass

    main_logger.info("Using Twisted reactor {0}".format(reactor.__class__))


    import urllib2
    import time
    retrys = 0
    while retrys < 180:
        try:
                urllib2.urlopen('http://localhost:8001', timeout=1)
        except urllib2.HTTPError, e:
            main_logger.info("crossbar instance gefunden.")
            break
        except Exception, e:
            main_logger.info("warte auf crossbar instance, versuche es in 1 Sec. wieder.")
        else:
            main_logger.info("crossbar instance gefunden.")
            break
        time.sleep(1.0)
        retrys +=1

    # create embedded web server for static files
    # wwwroot
    root = File("./wwwroot/")
    # messungenroot
    root.putChild("messungen", File(args.csvpath))
    # logroot
    root.putChild("logs", File("./logs/"))
    try:
        reactor.listenTCP(args.web, Site(root))
    except CannotListenError, e:
        main_logger.critical('Webserver konnte nicht gestrarted werden, port belegt? Fehlermeldung: :' + str(e))
        exit()

    # run WAMP application component
    ##
    from autobahn.twisted.wamp import ApplicationRunner

    runner = ApplicationRunner(args.router.decode("utf8"), u"me_gsv6",
                               extra={'port': args.port, 'baudrate': args.baudrate, 'csvpath': args.csvpath})

    # start the component and the Twisted reactor ..
    ##
    try:
        runner.run(McuComponent)
    except ConnectionRefusedError, e:
        main_logger.critical('WAMP Router konnte nicht erreicht werden, crossbar gestartet? Fehlermeldung: ' + str(e))
    except TCPTimedOutError, e:
        main_logger.critical('WAMP Router konnte nicht erreicht werden, richtige IP? Fehlermedlung: ' + str(e))
    except Exception, e:
        main_logger.critical('[start] Unexpected error: ' + str(e))
    finally:
        main_logger.info('serial2ws closing cleanly / graceful')
        os.kill(os.getpid(), signal.SIGTERM)