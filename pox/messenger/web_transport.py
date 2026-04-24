# Copyright 2011,2012 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Connects the POX messenger bus to HTTP.

Requires the "webserver" component.

NOTE: The web_transport keeps its own session IDs.  Since it was first
      written, though, sessions IDs have become part of every
      Connection, and we could (but are not) reuse those.
"""

from socketserver import ThreadingMixIn
from http.server import *
import time
import select

import random
import hashlib
import base64
import json

from pox.lib.recoco import Timer

from pox.messenger import Connection, Transport

from pox.core import core

from pox.web.webcore import *

log = core.getLogger()


class HTTPConnection (Connection):
  def __init__ (self, transport):
    Connection.__init__(self, transport)
    self._messages = []
    self._cond = threading.Condition()
    self._quitting = False

    # We're really protected from attack by the session key, we hope
    self._tx_seq = -1 #random.randint(0, 1 << 32)
    self._rx_seq = None

    #self._t = Timer(10, lambda : self.send({'hi':'again'}), recurring=True)

    self._touched = time.time()

    self._send_welcome()

  def _check_timeout (self):
    pass

  def _new_tx_seq (self):
    pass

  def _check_rx_seq (self, seq):
    pass

  def _close (self):
    super(HTTPConnection, self)._close()
    #TODO: track request sockets and cancel them?
    self._quitting = True

  def send_raw (self, data):
    self._cond.acquire()
    self._messages.append(data)
    self._cond.notify()
    self._cond.release()

  def _do_rx_message (self, items):
    pass


class HTTPTransport (Transport):
  def __init__ (self, nexus = None):
    Transport.__init__(self, nexus)
    self._connections = {}
    #self._t = Timer(5, self._check_timeouts, recurring=True)
    self._t = Timer(60*2, self._check_timeouts, recurring=True)

  def _check_timeouts (self):
    pass

  def _forget (self, connection):
    # From MessengerTransport
    if connection._session_id in self._connections:
      del self._connections[connection._session_id]
    else:
      #print "Failed to forget", connection
      pass

  def create_session (self):
    pass

  def get_session (self, key):
    pass



class CometRequestHandler (SplitRequestHandler):
  protocol_version = 'HTTP/1.1'

#  def __init__ (self, *args, **kw):
#    super(CometRequestHandler, self).__init__(*args, **kw)

  def _init (self):
    self.transport = self.args['transport']
    self.auth_function = self.args.get('auth', None)

  def _doAuth (self):
    pass

  def _getSession (self):
    pass

  def _enter (self):
    pass

  def do_POST (self):
    pass

  def do_GET (self):
    pass


def launch (username='', password=''):
  pass
