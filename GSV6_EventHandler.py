# -*- coding: utf-8 -*-
from CSVreducer import CSVreducer

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
import glob
import os
import sys
from datetime import datetime
import GSV6_UnitCodes
from Queue import Empty

from autobahn.wamp.types import RegisterOptions

spezialOptions = RegisterOptions(details_arg="details")


class GSVeventHandler():
    # here we register all "wamp" functions and all "wamp" listners around GSV-6CPU-Modul
    def __init__(self, session, gsv_lib, antwortQueue, frameRouter):
        self.session = session
        self.gsv_lib = gsv_lib
        self.antwortQueue = antwortQueue
        self.frameRouter = frameRouter
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
        self.session.register(self.shutdownSystem, u"de.me_systeme.gsv.shutdownSystem")
        self.session.register(self.getLogFileList, u"de.me_systeme.gsv.getLogFileList")
        self.session.register(self.reduceCSVFile, u"de.me_systeme.gsv.reduceCSVFile")

    def startStopTransmisson(self, start, hasToWriteCSVdata=False, **kwargs):
        if start:
            msg = 'Start Transmission. Call from ' + str(kwargs['details'].caller)
            logging.getLogger('serial2ws.WAMP_Component.router.GSVeventHandler').info(msg)
            data = self.gsv_lib.buildStartTransmission()
            self.frameRouter.setStartTimeStampStr(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), hasToWriteCSVdata)
        else:
            msg = 'Stop Transmission. Call from ' + str(kwargs['details'].caller)
            logging.getLogger('serial2ws.WAMP_Component.router.GSVeventHandler').info(msg)
            data = self.gsv_lib.buildStopTransmission()
            self.frameRouter.writeCSVdata()
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
            unit_str = GSV6_UnitCodes.unit_code_to_shortcut.get(unitNo)
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
        inputType = self.gsv_lib.convertIntToBytes(inputTypeValue)
        # SensIndex is always 0x00 (GSV-6)
        sensIndex = 0x00
        self.session.writeAntwort(self.gsv_lib.buildWriteInputType(channelNo, sensIndex, inputType),
                                  'rcvWriteInputType',
                                  channelNo)

    def getCachedConfig(self):
        return self.gsv_lib.getCachedConfig()

    def setDateTimeFromBrowser(self, dateTimeStr):
        if sys.platform == 'win32':
            logging.getLogger('serial2ws.WAMP_Component.router.GSVeventHandler').error(
                "setDateTime; Windows not supported")
            return [0x01, "Windows not supported"]
        else:
            x = os.system("sudo date -u -s \"%s\"" % (dateTimeStr))
            if x == 0:
                logging.getLogger('serial2ws.WAMP_Component.router.GSVeventHandler').debug("setDateTime; wurde gesetzt")
                return [0, "ERR_OK", dateTimeStr]
            else:
                logging.getLogger('serial2ws.WAMP_Component.router.GSVeventHandler').error(
                    "setDateTime; an error occurred: " + str(x))
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

    def shutdownSystem(self):
        if sys.platform == 'win32':
            return [0x01, "Windows not supported"]
        else:
            x = os.system("sudo shutdown -h now")
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
                logging.getLogger('serial2ws.WAMP_Component.router.GSVeventHandler').critical(msg)
                return False
            else:
                return True
        else:
            msg = fileName + ' konnte nicht gefunden werden (gelÃ¶scht werden)'
            logging.getLogger('serial2ws.WAMP_Component.GSV_6Protocol').warning(msg)
            return False

    def reduceCSVFile(self, fileName):
        filepath = self.session.config.extra['csvpath'] + fileName
        if (os.path.isfile(filepath)):
            reducer = CSVreducer(fileName, self.session.config.extra['csvpath'])
            reducer.start()
            return True
        else:
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
            logging.getLogger('serial2ws.WAMP_Component.router.GSVeventHandler').critical(msg)
            return False
