# -*- coding: utf-8 -*-
from GSV6_AntwortFrameHandler import AntwortFrameHandler
from GSV6_EventHandler import GSVeventHandler
from GSV6_MessFrameHandler import MessFrameHandler

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
from time import sleep
from Queue import Queue, Empty, Full
from GSV6_SeriallLib import GSV6_seriall_lib


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
                    logging.getLogger('serial2ws.WAMP_Component.router.ThreadingWaitForFirmwareVersion').critical(
                        "wait for cache...; after 10 retrys, please restart application.")
                else:
                    logging.getLogger('serial2ws.WAMP_Component.router.ThreadingWaitForFirmwareVersion').info(
                        "wait for cache...")
                sleep(0.5)


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
        self.messFrameEventHandler = MessFrameHandler(self.session, self.gsv6)
        self.antwortFrameEventHandler = AntwortFrameHandler(self.session, self.gsv6, self.eventHandler,
                                                            self.antwortQueue, self.messFrameEventHandler)

        self.waitFirmwareVersionThread = ThreadingWaitForFirmwareVersion(self.session, self.gsv6)
        # fallback, this flag kills this thread if main thread killed
        self.daemon = True

    def run(self):
        # arbeits Thread: router -> routen von AntwortFrames und MessFrames
        FrameRouter.lock.acquire()
        self.running = True
        FrameRouter.lock.release()
        logging.getLogger('serial2ws.WAMP_Component.router').info('started')

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
                logging.getLogger('serial2ws.WAMP_Component.router').trace('new Frame: ' + newFrame.toString())
                if newFrame.getFrameType() == 0:
                    # MesswertFrame
                    self.messFrameEventHandler.computeFrame(newFrame)
                elif newFrame.getFrameType() == 1:
                    # AntwortFrame
                    self.antwortFrameEventHandler.computeFrame(newFrame)
                else:
                    # error
                    logging.getLogger('serial2ws.WAMP_Component.router').debug(
                        'nothing to do with an FrameType != Messwert/Antwort')

        logging.getLogger('serial2ws.WAMP_Component.router').info('exit')

    def stop(self):
        FrameRouter.lock.acquire()
        self.running = False
        FrameRouter.lock.release()
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
            logging.getLogger('serial2ws.WAMP_Component.router').info('try to reach GSV-6CPU ...')

            self.session.write(data)
            sleep(1.0)
            if not self.frameQueue.empty():
                frame = self.frameQueue.get()
                if frame.getAntwortErrorCode() != 0x00:
                    logging.getLogger('serial2ws.WAMP_Component.router').critical(
                        'error init modul-communication. re-try...')

                    self.frameQueue.queue.clear()
                    sleep(1.0)
                else:
                    logging.getLogger('serial2ws.WAMP_Component.router').info('GSV-6CPU found.')
                    self.frameQueue.queue.clear()
                    # fill cache
                    self.eventHandler.getDataRate()
                    self.eventHandler.getReadInputType(1)
                    # because GSV-6 only supports one InputType for all channels
                    '''
                    self.eventHandler.getReadInputType(2)
                    self.eventHandler.getReadInputType(3)
                    self.eventHandler.getReadInputType(4)
                    self.eventHandler.getReadInputType(5)
                    self.eventHandler.getReadInputType(6)
                    '''
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
                logging.getLogger('serial2ws.WAMP_Component.router').info(msg)
                sleep(5.0)