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
#
# Based on WebSocket/WAMP Serial2ws Example (https://github.com/tavendo/AutobahnPython/tree/master/examples/twisted/wamp/app/serial2ws)
# Dependencies:
#   Autobahn    http://autobahn.ws/         (MIT License)
#
###############################################################################

from twisted.internet.defer import inlineCallbacks
from twisted.python import log as logTwisted
from autobahn.twisted.wamp import ApplicationSession
from autobahn.wamp.types import RegisterOptions
from autobahn.twisted.wamp import ApplicationRunner

spezialOptions = RegisterOptions(details_arg="details")

import logging


class McuComponent(ApplicationSession):
    """
    RPi WAMP application component.
    """

    # cleanup here
    def leave(self):
        pass

    @inlineCallbacks
    def onJoin(self, details):
        print("MyComponent ready! Configuration: {}".format(self.config.extra))
        debug = self.config.extra['debug']

        yield self.subscribe(self.onMesswertReceived,u'de.me_systeme.gsv.onMesswertReceived')
        yield self.subscribe(self.onStartStopTransmission,u'de.me_systeme.gsv.onStartStopTransmission');

    def onMesswertReceived(self,args):
        args = args[0]
        print(args.get(u'channel0_value'))

        # value of channel 1
        # args.get(u'channel0_value')

        # value of channel 2
        # args.get(u'channel1_value')

        # value of channel 3
        # args.get(u'channel2_value')

        # value of channel 4
        # args.get(u'channel3_value')

        # value of channel 5
        # args.get(u'channel4_value')

        # value of channel 6
        # args.get(u'channel5_value')

    def onStartStopTransmission(self, args):
        if args[2]:
            print("Messung gestartet")
        else:
            print("Messung gestoppt")

    def __exit__(self):
        print('Exit.')

    def __del__(self):
        print('del.')


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

    parser.add_argument("--router", type=str, default=None,
                        help='If given, connect to this WAMP router. Else run an embedded router on 8080.')

    args = parser.parse_args()

    logTwisted.startLogging(sys.stdout)


    # run WAMP application component
    ##

    router = args.router or u'ws://127.0.0.1:8080/ws/'

    runner = ApplicationRunner(router, u"me_gsv6",
                               extra={'debug': True})
    # extra={'port': args.port, 'baudrate': args.baudrate, 'debug': args.debug})

    # start the component and the Twisted reactor ..
    ##
    runner.run(McuComponent)
