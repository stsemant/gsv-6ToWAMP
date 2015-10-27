# -*- coding: utf-8 -*-
from CSVwriter import CSVwriter

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
from datetime import datetime
import numpy as np
from collections import deque
import GSV6_UnitCodes

maxCacheMessCount = 1000


class MessFrameHandler():
    def __init__(self, session, gsv_lib):
        self.session = session
        self.gsv_lib = gsv_lib
        self.messCounter = 0
        self.startTimeStampStr = ''
        self.hasTOWriteCSV = False
        self.messData = [deque([], 10), deque([], 10), deque([], 10), deque([], 10), deque([], 10), deque([], 10)]
        self.reduceCounter = 0
        self.dataRateReduceFactor = 1

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

        # reducce data-set
        hasToReduceDataSet = False
        try:
            if float(self.gsv_lib.getCachedProperty('DataRate', 'DataRate')) > 50.0:
                hasToReduceDataSet = True
        except Exception, e:
            logging.getLogger('serial2ws.WAMP_Component.router.MessFrameHandler').debug(
                'can\'t detect DataRate: ' + str(e))
        if not hasToReduceDataSet:
            # publish WAMP event to all subscribers on topic
            self.session.publish(u"de.me_systeme.gsv.onMesswertReceived", [payload, inputOverload, sixAchisError])
            logging.getLogger('serial2ws.WAMP_Component.router.MessFrameHandler').trace(
                'Received MessFrame: published.')
        else:
            try:
                payload2 = payload.copy()
                for i in range(0, len(values)):
                    self.messData[i].append(values[i])
                self.reduceCounter += 1
                if self.reduceCounter >= self.dataRateReduceFactor:
                    self.reduceCounter = 0

                    for i in range(0, len(values)):
                        # there is no append/add function for Python Dictionaries
                        x1 = np.amax(list(self.messData[i]))[0]
                        x2 = np.amin(list(self.messData[i]))[0]
                        f = -1
                        for k in range(0, len(self.messData[i])):
                            if x1 == list(self.messData[i])[k]:
                                f = 1
                                break
                            elif x2 == list(self.messData[i])[k]:
                                f = 2
                                break
                        if f == 2:
                            x3 = x1
                            x1 = x2
                            x2 = x3
                        payload[u'channel' + str(counter) + '_value'] = x1
                        payload2[u'channel' + str(counter) + '_value'] = x2
                    self.session.publish(u"de.me_systeme.gsv.onMesswertReceived",
                                         [payload, inputOverload, sixAchisError])
                    self.session.publish(u"de.me_systeme.gsv.onMesswertReceived",
                                         [payload2, inputOverload, sixAchisError])
                    logging.getLogger('serial2ws.WAMP_Component.router.MessFrameHandler').trace(
                        'Received MessFrame: published. was reduced!')
            except Exception, e:
                logging.getLogger('serial2ws.WAMP_Component.router.MessFrameHandler').critical(
                    'can\'t compute reduced messFrame: ' + str(e))

    def setStartTimeStamp(self, startTimeStampStr, hasToWriteCSV):
        self.startTimeStampStr = startTimeStampStr
        self.hasTOWriteCSV = hasToWriteCSV

    def writeCSVdataNow(self, startTimeStampStr=''):
        # build unit index
        units = []
        if self.gsv_lib.isConfigCached('UnitNo', 1):
            units.append(GSV6_UnitCodes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 1)))
        else:
            units.append('undefined')
        if self.gsv_lib.isConfigCached('UnitNo', 2):
            units.append(GSV6_UnitCodes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 2)))
        else:
            units.append('undefined')
        if self.gsv_lib.isConfigCached('UnitNo', 3):
            units.append(GSV6_UnitCodes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 3)))
        else:
            units.append('undefined')
        if self.gsv_lib.isConfigCached('UnitNo', 4):
            units.append(GSV6_UnitCodes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 4)))
        else:
            units.append('undefined')
        if self.gsv_lib.isConfigCached('UnitNo', 5):
            units.append(GSV6_UnitCodes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 5)))
        else:
            units.append('undefined')
        if self.gsv_lib.isConfigCached('UnitNo', 6):
            units.append(GSV6_UnitCodes.unit_code_to_shortcut.get(self.gsv_lib.getCachedProperty('UnitNo', 6)))
        else:
            units.append('undefined')

        # start csvWriter
        writer = CSVwriter(self.startTimeStampStr, self.session.messCSVDictList, self.session.messCSVDictList_lock,
                           units, self.session,
                           self.session.config.extra['csvpath'])
        writer.start()

    def resize_deque(self, d, newSize):
        if d.maxlen > newSize:
            return deque(list(d)[-newSize:], newSize)
        else:
            return deque(d, newSize)

    def dataRateChanged(self, newDataRateFactor):
        logging.getLogger('serial2ws.WAMP_Component.router.MessFrameHandler').info(
            'new data-set-reduce-factor is ' + str(newDataRateFactor))
        self.dataRateReduceFactor = newDataRateFactor
        for i in range(0, len(self.messData)):
            self.messData[i] = self.resize_deque(self.messData[i], newDataRateFactor)
