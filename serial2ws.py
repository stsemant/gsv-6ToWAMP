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

import numpy as np
from collections import deque

import error_codes
import GSV6_BasicFrameType
# import Queue
from Queue import Queue
import logging

import unit_codes
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 'format': '
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# formatter = logging.Formatter('[%(levelname)s] %(message)s [%(module)s %(funcName)s %(lineno)d]')
# logger.setFormatter(formatter)
class GSV_6Protocol(protocol.Protocol):
    inDataBuffer = {}
    trace = False

    def __init__(self, session, frameQueue, anfrageQueue, debug=False):
        self.debug = debug
        self.session = session
        self.inDataBuffer = bytearray()
        self.frameQueue = frameQueue
        self.anfrageQueue = anfrageQueue

    def dataReceived(self, data):
        self.inDataBuffer.extend(data)
        logger.debug('[' + __name__ + '] serial data received.')
        '''
        if self.trace:
            print('[serial|data received] ')# + ' '.join(format(x, '02x') for x in data))
        '''
        self.checkForCompleteFrame()

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
                        '[serial] Received compelte Frame: ' + ' '.join(format(x, '02x') for x in bytearray(tempArray)))

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

    def controlLed(self, str):
        """
        This method is exported as RPC and can be called by connected clients
        """
        print('[from Website] ' + str)
        # self.transport.write(payload)

    def write(self, data):
        self.transport.write(data)

class MessFrameHandler():
    def __init__(self, session, gsv_lib, eventHandler):
        self.session = session
        self.gsv_lib = gsv_lib
        self.eventHandler = eventHandler

    def computeFrame(self, frame):
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
        # publish WAMP event to all subscribers on topic
        self.session.publish(u"de.me_systeme.gsv.onMesswertReceived", [payload, inputOverload, sixAchisError])


class AntwortFrameHandler():
    # thread-safe? nothing to do here -> queue-Object is an thread-safe

    def __init__(self, session, gsv_lib, eventHandler, queue):
        self.session = session
        self.gsv_lib = gsv_lib
        self.eventHandler = eventHandler
        self.queue = queue

    def computeFrame(self, frame):
        try:
            if not self.queue.empty():
                function_informations = self.queue.get_nowait()
                methodNameToCall, args = function_informations.popitem()
                methodToCall = getattr(self, methodNameToCall)
                if args is not None:
                    result = methodToCall(frame, args)
                else:
                    result = methodToCall(frame)
        except:
            msg = "Unexpected error:" + str(sys.exc_info()[0])
            self.session.addError(msg)

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

    def rcvGetUnitNo(self, frame, channelNo):
        unit_str = unit_codes.unit_code_to_shortcut.get(frame.getPayload()[0])
        self.session.publish(u"de.me_systeme.gsv.onGetUnitNo", [frame.getAntwortErrorCode(), channelNo, unit_str])

    def rcvGetGetInterface(self, frame, ubertragung=None):
        reuslt = self.gsv_lib.decodeGetInterface(frame.getPayload())
        self.session.publish(u"de.me_systeme.gsv.onGetInterface", reuslt)

    def rcvGetReadAoutScale(self, frame, channelNo):
        values = self.gsv_lib.convertToFloat(frame.getPayload())
        self.session.publish(u"de.me_systeme.gsv.onGetReadAoutScale",
                             [frame.getAntwortErrorCode(), channelNo, values[0]])


class GSVeventHandler():
    # here we register all "wamp" functions and all "wamp" listners around GSV-6CPU-Modul
    def __init__(self, session, gsv_lib, antwortQueue):
        self.session = session
        self.gsv_lib = gsv_lib
        self.antwortQueue = antwortQueue
        # start register
        self.regCalls()

    def regCalls(self):
        self.session.register(self.startStopTransmisson, u"de.me_systeme.gsv.startStopTransmission")
        self.session.register(self.getUnitText, u"de.me_systeme.gsv.getUnitText")
        self.session.register(self.setUnitText, u"de.me_systeme.gsv.setUnitText")
        self.session.register(self.getUnitNo, u"de.me_systeme.gsv.getUnitNo")
        self.session.register(self.getGetInterface, u"de.me_systeme.gsv.getGetIntetface")
        self.session.register(self.getReadAoutScale, u"de.me_systeme.gsv.getReadAoutScale")

    def startStopTransmisson(self, start):
        if start:
            print('Start Transmission.')
            data = self.gsv_lib.buildStartTransmission()
        else:
            print('Stops Transmission.')
            data = self.gsv_lib.buildStopTransmission()
        self.session.writeAntwort(data, 'rcvStartStopTransmission', start)

    def getUnitText(self):
        self.session.writeAntwort(self.gsv_lib.buildGetUnitText(), 'rcvGetUnitText')

    def setUnitText(self, text):
        self.session.writeAntwort(self.gsv_lib.buildSetUnitText(text), 'rcvSetUnitText')

    def getUnitNo(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildGetUnitNo(channelNo), 'rcvGetUnitNo', channelNo)

    def getGetInterface(self, ubertragung=None):
        self.session.writeAntwort(self.gsv_lib.buildGetInterface(ubertragung), 'rcvGetGetInterface', ubertragung)

    def getReadAoutScale(self, channelNo):
        self.session.writeAntwort(self.gsv_lib.buildReadAoutScale(channelNo), 'rcvGetReadAoutScale', channelNo)


import threading
from gsv6_seriall_lib import GSV6_seriall_lib


class FrameRouter(threading.Thread):
    # lock for running variale, nötig?
    lock = threading.Lock()

    def __init__(self, session, frameQueue, antwortQueue, debug=False):
        threading.Thread.__init__(self)
        self.debug = debug
        self.session = session
        self.frameQueue = frameQueue
        self.antwortQueue = antwortQueue
        self.running = False

        # GSV-6CPU Lib
        self.gsv6 = GSV6_seriall_lib()
        self.eventHandler = GSVeventHandler(self.session, self.gsv6, antwortQueue)
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
                    print('[router] ' + newFrame.toString())
                if newFrame.getFrameType() == 0:
                    # MesswertFrame
                    self.messFrameEventHandler.computeFrame(newFrame)
                elif newFrame.getFrameType() == 1:
                    # AntwortFrame
                    self.antwortFrameEventHandler.computeFrame(newFrame)
                    pass
                else:
                    # error
                    print('nothing to do with an FrameType != Messwert/Antwort')

        print("[router] exit loop.")

    def stop(self):
        FrameRouter.lock.acquire()
        self.running = False
        FrameRouter.lock.release()


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

    # to ensure that we have a thead-safe write function, we need that look
    serialWrite_lock = threading.Lock()
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

        # create an router object/thread
        self.router = FrameRouter(self, self.frameInBuffer, self.antwortQueue, debug)
        self.router.start()

        # serialProtocol = McuProtocol(self, debug)
        serialProtocol = GSV_6Protocol(self, self.frameInBuffer, self.antwortQueue, debug)

        print('About to open serial port {0} [{1} baud] ..'.format(port, baudrate))
        try:
            self.serialPort = SerialPort(serialProtocol, port, reactor, baudrate=baudrate)
        except Exception as e:
            print('Could not open serial port: {0}'.format(e))
            self.leave()
        else:
            yield self.register(serialProtocol.controlLed, u"com.myapp.mcu.control_led")

    def __exit__(selfself):
        print('Exit.')

    def __del__(selfself):
        print('del.')

    def getErrors(self):
        return list(self.errorQueue)

    def addError(self, errorString):
        self.errorQueue.append(errorString)
        self.publish(u"de.me_systeme.gsv.onError", errorString)

    def writeAntwort(self, data, functionName, args=None):
        # okay this function have to be atomic
        # we protect it with a lock!
        self.serialWrite_lock.acquire()
        try:
            self.antwortQueue.put_nowait({functionName: args})
            self.serialPort.write(data)
            print('[MyComp|write] Data: ' + ' '.join(format(z, '02x') for z in data))
            msg = '[MyComp|write] Data: ' + ' '.join(format(z, '02x') for z in data)
            self.addError(msg)
        except NameError:
            if self.debug:
                print('[MyComp] serialport not openend')
        finally:
            self.serialWrite_lock.release()

    def write(self, data):
        # okay this function have to be atomic
        # we protect it with a lock!
        self.serialWrite_lock.acquire()
        try:
            self.serialPort.write(data)
            print('[MyComp|write] Data: ' + ' '.join(format(z, '02x') for z in data))
            str = '[MyComp|write] Data: ' + ' '.join(format(z, '02x') for z in data)
            self.addError(str)
        except NameError:
            if self.debug:
                print('[MyComp] serialport not openend')
        finally:
            self.serialWrite_lock.release()

    def publish_test(self, topic, args):
        self.publish(topic, args)


if __name__ == '__main__':

    import sys
    import argparse
    # log.setLevel(logging.DEBUG)
    # parse command line arguments
    ##
    parser = argparse.ArgumentParser()

    parser.add_argument("-d", "--debug", action="store_true",
                        help="Enable debug output.")

    parser.add_argument("--baudrate", type=int, default=115200,
                        choices=[300, 1200, 2400, 4800, 9600, 19200, 57600, 115200],
                        help='Serial port baudrate.')

    parser.add_argument("--port", type=str, default='12',
                        help='Serial port to use (e.g. 3 for a COM port on Windows, /dev/ttyATH0 for Arduino Yun, /dev/ttyACM0 for Serial-over-USB on RaspberryPi.')

    parser.add_argument("--web", type=int, default=8000,
                        help='Web port to use for embedded Web server. Use 0 to disable.')

    parser.add_argument("--router", type=str, default=None,
                        help='If given, connect to this WAMP router. Else run an embedded router on 8080.')

    args = parser.parse_args()

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

        reactor.listenTCP(args.web, Site(File(".")))

    # run WAMP application component
    ##
    from autobahn.twisted.wamp import ApplicationRunner

    router = args.router or u'ws://127.0.0.1:8080/ws/'

    runner = ApplicationRunner(router, u"crossbardemo",
                               extra={'port': args.port, 'baudrate': args.baudrate, 'debug': True})
    # extra={'port': args.port, 'baudrate': args.baudrate, 'debug': args.debug})

    # start the component and the Twisted reactor ..
    ##
    runner.run(McuComponent)
