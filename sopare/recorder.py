#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (C) 2015 - 2017 Martin Kauss (yo@bishoph.org)

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""

import pyaudio
import multiprocessing
import buffering
import time
import sys
import io
import config
import hatch
import numpy
import visual
import logging

class recorder():

    def __init__(self, hatch):
        self.hatch = hatch
        self.FORMAT = pyaudio.paInt16
        # mono
        self.CHANNELS = 1
        self.pa = pyaudio.PyAudio()
        self.queue = multiprocessing.JoinableQueue()
        self.running = True
        self.visual = visual.visual()
  
        # logging ###################
        self.logger = self.hatch.get('logger').getlog()
        self.logger = logging.getLogger(__name__)

        defaultCapability = self.pa.get_default_host_api_info()
        self.logger.debug(defaultCapability)

        self.stream = self.pa.open(format=self.FORMAT,
                channels=self.CHANNELS,
                rate=config.SAMPLE_RATE,
                input=True,
                output=False,
                frames_per_buffer=config.CHUNK)

        self.buffering = buffering.buffering(self.hatch, self.queue)
        if (hatch.get('infile') == None):
            self.recording()
        else:
            self.readfromfile()

    def readfromfile(self):
        self.logger.info("* reading file " + self.hatch.get('infile'))
        file = io.open(self.hatch.get('infile'), 'rb', buffering=config.CHUNK)
        while True:
            buf = file.read(config.CHUNK * 2)
            if buf:
                self.queue.put(buf)
                if (self.hatch.get('plot') == True):
                    data = numpy.fromstring(buf, dtype=numpy.int16)
                    self.hatch.extend_plot_cache(data)
            else:
                self.queue.close()
                break
        file.close()
        once = False
        if (self.hatch.get('plot') == True):
            self.visual.create_sample(self.hatch.get_plot_cache(), 'sample.png')
        while (self.queue.qsize() > 0):
            if (once == False):
                self.logger.debug('waiting for queue to finish...')
                once = True
            time.sleep(.1) # wait for all threads to finish their work
        self.queue.close()
        self.buffering.flush('end of file')
        self.logger.info("* done ")
        self.stop()
        sys.exit()

    def recording(self):
        self.logger.info("start endless recording")
        while self.running:
            try:
                if (self.buffering.is_alive()):
                    buf = self.stream.read(config.CHUNK)
                    self.queue.put(buf)
                else:
                    self.logger.info("Buffering not alive, stop recording")
                    self.queue.close()
                    break
            except IOError as e:
                self.logger.warning("stream read error "+str(e))

        self.stop()
        sys.exit()

    def stop(self):
        self.logger.info("stop endless recording")
        self.running = False
        try:
            self.queue.join_thread()
            self.buffering.terminate()
        except:
            pass
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
