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

import logging
import threading
from autobahn.twisted.wamp import ApplicationSession
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.serialport import SerialPort
from LoggingWAMP_Handler import WAMP_LoggingHandler, NoHTTP_GetFilter
from datetime import datetime
from collections import deque
from Queue import Queue

import os
import signal
from GSV6_Protocol import GSV_6Protocol
from GSV6_FrameRouter import FrameRouter

from time import sleep


class WAMP_Component(ApplicationSession):
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
            self.serialPort.stopReading()
        except Exception:
            pass
        try:
            self.serialPort.stopReading()
            self.serialPort.reactor.stop()
        except Exception:
            pass
        if self.router.isAlive():
            self.router.stop()
            # wait max 1 Sec.
            self.router.join(1.0)

    @inlineCallbacks
    def onJoin(self, details):
        port = self.config.extra['port']
        baudrate = self.config.extra['baudrate']

        # install signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.toWAMP_logger = WAMP_LoggingHandler(self, self.logQueue)
        self.toWAMP_logger.addFilter(NoHTTP_GetFilter())
        logging.getLogger('serial2ws').addHandler(self.toWAMP_logger)


        # first of all, register the getErrors Function
        yield self.register(self.getLog, u"de.me_systeme.gsv.getLog")
        yield self.register(self.getIsSerialConnected, u"de.me_systeme.gsv.getIsSerialConnected")

        # create an router object/thread
        self.router = FrameRouter(self, self.frameInBuffer, self.antwortQueue)

        # create GSV6 Serial-Protocol-Object
        serialProtocol = GSV_6Protocol(self, self.frameInBuffer, self.antwortQueue)

        logging.getLogger('serial2ws.WAMP_Component').debug(
            'About to open serial port {0} [{1} baud] ..'.format(port, baudrate))

        # try to init Serial-Connection
        try:
            self.serialPort = SerialPort(serialProtocol, port, reactor, baudrate=baudrate)
            self.isSerialConnected = True
        except Exception as e:
            logging.getLogger('serial2ws.WAMP_Component').critical('Could not open serial port: {0}. exit!'.format(e))
            os.kill(os.getpid(), signal.SIGTERM)
        else:
            # when erial-init okay -> start FrameRouter
            self.router.start()

    def __exit__(self):
        logging.getLogger('serial2ws.WAMP_Component').trace('Exit.')

    def __del__(self):
        logging.getLogger('serial2ws.WAMP_Component').trace('del.')

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
                    logging.getLogger('serial2ws.WAMP_Component').debug(
                        "serialWait, prevent GSV-6CPU RX Buffer overflow")
                    sleep(0.2)  # Time in seconds
            else:
                self.sendCounter = 0
        try:
            self.antwortQueue.put_nowait({functionName: args})
            self.serialPort.write(str(data))
            logging.getLogger('serial2ws.WAMP_Component').debug(
                '[serialWrite] Data: ' + ' '.join(format(z, '02x') for z in data))
        except NameError:
            logging.getLogger('serial2ws.WAMP_Component').debug('[WAMP_Component] serialport not openend')
        finally:
            self.lastTime = datetime.now()
            self.serialWrite_lock.release()

    def write(self, data):
        # okay this function have to be atomic
        # we protect it with a lock!
        self.serialWrite_lock.acquire()
        try:
            self.serialPort.write(str(data))
            logging.getLogger('serial2ws.WAMP_Component').debug(
                '[serialWrite] Data: ' + ' '.join(format(z, '02x') for z in data))
        except NameError:
            logging.getLogger('serial2ws.WAMP_Component').debug('serialport not openend')
        finally:
            self.serialWrite_lock.release()

    def getIsSerialConnected(self):
        return self.isSerialConnected

    def lostSerialConnection(self, errorMessage):
        logging.getLogger('serial2ws.WAMP_Component').critical("Lost SerialConnection: " + errorMessage)
        self.isSerialConnected = False
        # not implemented at web-frontend
        self.publish(u"de.me_systeme.gsv.onSystemGoingDown")
        # shut down app
        os.kill(os.getpid(), signal.SIGTERM)

    def signal_handler(self, signal, frame):
        logger = logging.getLogger('serial2ws')
        logger.removeHandler(self.toWAMP_logger)
        self.disconnect()
