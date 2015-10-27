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
import collections
import GSV6_UnitCodes
import numpy as np


class AntwortFrameHandler():
    # thread-safe? nothing to do here -> queue-Object is an thread-safe

    def __init__(self, session, gsv_lib, eventHandler, queue, messFrameHandler):
        self.session = session
        self.gsv_lib = gsv_lib
        self.eventHandler = eventHandler
        self.messFrameHandler = messFrameHandler
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
            logging.getLogger('serial2ws.WAMP_Component.router.AntwortFrameHandler').critical(msg)

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
        self.gsv_lib.addConfigToCache('Varianz', channelNo, np.var([-(value * 1.05), value * 1.05]))
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
        unit_str = GSV6_UnitCodes.unit_code_to_shortcut.get(frame.getPayload()[0])
        self.session.publish(u"de.me_systeme.gsv.onGetUnitNoAsText",
                             [frame.getAntwortErrorCode(), channelNo, unit_str, frame.getAntwortErrorText()])

    def rcvGetUnitNo(self, frame, channelNo):
        # datatype-conversion
        unit_str = GSV6_UnitCodes.unit_code_to_shortcut.get(frame.getPayload()[0])
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
        # notify messFrameHandler
        self.messFrameHandler.dataRateChanged(int(float(dataRate) / 25.0))
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
        logging.getLogger('serial2ws.WAMP_Component.router.AntwortFrameHandler').info('cache ready.')
        self.session.sys_ready = True
        if frame.getAntwortErrorCode() == 0:
            self.gsv_lib.addConfigToCache('ME_ID', 'ME_ID', True)
            logging.getLogger('serial2ws.WAMP_Component.router.AntwortFrameHandler').info(
                'ME ID has been set successfully.')
        else:
            self.gsv_lib.addConfigToCache('ME_ID', 'ME_ID', False)
            logging.getLogger('serial2ws.WAMP_Component.router.AntwortFrameHandler').info("ME ID could not be set.")
