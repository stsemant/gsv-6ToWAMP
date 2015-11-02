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
import csv
from itertools import takewhile, repeat
from datetime import datetime


class CSVreducer(threading.Thread):
    def __init__(self, filename, path='./messungen/'):
        threading.Thread.__init__(self)
        self.path = path
        self.inputFilename = path + filename
        self.outfilename = self.path + 'red_' + filename

    # source http://stackoverflow.com/questions/845058/how-to-get-line-count-cheaply-in-python from Michael Bacon and Quentin Pradet
    def rawincount(self, filename):
        f = open(filename, 'rb')
        bufgen = takewhile(lambda x: x, (f.read(1024 * 1024) for _ in repeat(None)))
        return sum(buf.count(b'\n') for buf in bufgen)

    def run(self):
        try:
            c = self.rawincount(self.inputFilename)
            if c < 4000:
                logging.getLogger('serial2ws.WAMP_Component.router.GSVeventHandler.CSVreducer').debug(
                    'it is NOT necessary to reduce the CSV-File.')
                return
            logging.getLogger('serial2ws.WAMP_Component.router.GSVeventHandler.CSVreducer').debug(
                'CSVreducer started on a File with {} lines.'.format(c))
            steps = int(c / 4000)
            window = int(c / steps)
            steps += 1

            channel_names = []
            channel_max = {}
            channel_min = {}
            channel_timestamps = {}
            firstRound = True
            firstRow = True
            counter = 0

            with open(self.outfilename, 'wb') as rcsvfile:
                fieldnamesForWrite = ['timestamp']
                writer = csv.DictWriter(rcsvfile, fieldnames=fieldnamesForWrite, extrasaction='ignore')

                with open(self.inputFilename, 'rb') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        if firstRow:
                            channel_names = row.keys()
                            channel_names.remove('timestamp')
                            writer.fieldnames.extend(sorted(channel_names))
                            writer.writeheader()
                        for key in row.iterkeys():
                            if not str(key).startswith('timestamp'):
                                if firstRow:
                                    channel_max[key] = None
                                    channel_min[key] = None
                                    # channel_timestamps[key + '_max'] = None
                                    # channel_timestamps[key + '_min'] = None
                                x = float(row.get(key))
                                if firstRound:
                                    channel_timestamps[key + '_max'] = datetime.strptime(row.get('timestamp'),
                                                                                         '%Y-%m-%d %H:%M:%S.%f')
                                    channel_timestamps[key + '_min'] = datetime.strptime(row.get('timestamp'),
                                                                                         '%Y-%m-%d %H:%M:%S.%f')
                                    channel_max[key] = x
                                    channel_min[key] = x
                                else:
                                    if x > channel_max[key]:
                                        channel_max[key] = x
                                        channel_timestamps[key + '_max'] = datetime.strptime(row.get('timestamp'),
                                                                                             '%Y-%m-%d %H:%M:%S.%f')
                                    if x < channel_min[key]:
                                        channel_min[key] = x
                                        channel_timestamps[key + '_min'] = datetime.strptime(row.get('timestamp'),
                                                                                             '%Y-%m-%d %H:%M:%S.%f')
                        if firstRound:
                            firstRound = False
                            pass
                        counter += 1
                        firstRow = False
                        if counter >= window:
                            counter = 0
                            firstRound = True

                            # now write data
                            for channel in channel_names:
                                if channel_timestamps[channel + '_max'] < channel_timestamps[channel + '_min']:
                                    tmp = {}
                                    tmp['timestamp'] = channel_timestamps[channel + '_max']
                                    tmp[channel] = channel_max[channel]
                                    writer.writerow(tmp)
                                    tmp['timestamp'] = channel_timestamps[channel + '_min']
                                    tmp[channel] = channel_min[channel]
                                    writer.writerow(tmp)
                                else:
                                    tmp = {}
                                    tmp['timestamp'] = channel_timestamps[channel + '_min']
                                    tmp[channel] = channel_min[channel]
                                    writer.writerow(tmp)
                                    tmp['timestamp'] = channel_timestamps[channel + '_max']
                                    tmp[channel] = channel_max[channel]
                                    writer.writerow(tmp)
                logging.getLogger('serial2ws.WAMP_Component.router.GSVeventHandler.CSVreducer').debug(
                    'CSV-File written')
        except Exception, e:
            logging.getLogger('serial2ws.WAMP_Component.router.GSVeventHandler.CSVreducer').warning(
                'Exception: ' + str(e))
