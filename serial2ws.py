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

import logging
import logging.handlers
from twisted.python import log

import os
import sys
import argparse
from time import sleep
import signal
import time
import urllib2
from ConfigParser import SafeConfigParser

from twisted.internet.error import ConnectionRefusedError, TCPTimedOutError, ReactorAlreadyInstalledError, \
    CannotListenError
from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet import reactor

from GSV6_WAMP_Handler import WAMP_Component


# adding new log-level below debug
TRACE = 5
logging.addLevelName(TRACE, 'TRACE')

def trace(self, message, *args, **kws):
    self.log(TRACE, message, *args, **kws)

logging.Logger.trace = trace
logging.basicConfig()


# config
# after this amount, the data will be written to the CSV-File
maxCacheMessCount = 1000
# FileSize in MB for Logging
maxLogFileSize = 1


if __name__ == '__main__':

    if not os.path.exists("./logs"):
        os.makedirs("./logs")

    # init logging
    main_logger = logging.getLogger('serial2ws')
    log_file_handler = logging.handlers.RotatingFileHandler('./logs/app.log', maxBytes=1024 * 1024 * maxLogFileSize,
                                                            backupCount=4)
    formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s - %(message)s')
    log_file_handler.setFormatter(logging.Formatter('%(asctime)s [%(name)s] %(levelname)s - %(message)s'))
    main_logger.addHandler(log_file_handler)

    main_logger.setLevel(logging.DEBUG)

    # create Observer for pipe twisted log to python log
    observer = log.PythonLoggingObserver(loggerName='serial2ws.twisted')
    observer.start()

    # parse command line arguments
    ##
    parser = argparse.ArgumentParser()

    parser.add_argument("-l", "--log", type=str, default='DEBUG',
                        help="set logLevel (CRITICAL, ERROR, WARNING, INFO, DEBUG, TRACE).")

    parser.add_argument("--baudrate", type=int, default=230400,
                        choices=[300, 1200, 2400, 4800, 9600, 19200, 57600, 115200, 230400],
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

    if sys.platform == 'win32':
        parser.add_argument("-b", "--boot_wait", type=int, default=0,
                            help='add some waiting period, befor starting up [in Sec.].')
    else:
        parser.add_argument("-b", "--boot_wait", type=int, default=10,
                            help='add some waiting period, befor starting up [in Sec.].')

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

    retrys = 0
    while retrys < 180:
        try:
            # TODO die Url stimmt nicht mehr, wenn die crossbarinstanz auf einen andenrem Port und/oder unter einer anderen URL erreichbar ist.
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
        retrys += 1

    if args.boot_wait > 0:
        main_logger.info("waiting {0} sec to start...".format(args.boot_wait))
        sleep(args.boot_wait)

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
        runner.run(WAMP_Component)
    except ConnectionRefusedError, e:
        main_logger.critical('WAMP Router konnte nicht erreicht werden, crossbar gestartet? Fehlermeldung: ' + str(e))
    except TCPTimedOutError, e:
        main_logger.critical('WAMP Router konnte nicht erreicht werden, richtige IP? Fehlermedlung: ' + str(e))
    except Exception, e:
        main_logger.critical('[start] Unexpected error: ' + str(e))
    finally:
        main_logger.info('serial2ws closing cleanly / graceful')
        os.kill(os.getpid(), signal.SIGTERM)
