# Copyright 2012 James McCauley
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
Connects the POX messenger bus to a JSON-RPC based web client.
Requires the "webserver" and "messenger" components.

A disclaimer:
  I think the term "AJAX" is dumb.  But this module was
  originally called httpjsonrpc_transport and had classes with
  names like HTTPJSONRPCConnection and I just couldn't take it.
"""

import time
import select
import threading

from pox.core import core
from pox.web.jsonrpc import JSONRPCHandler, make_error, ABORT
from pox.lib.recoco import Timer
from pox.messenger import Connection, Transport

log = core.getLogger()

SESSION_TIMEOUT = 60#120 # Seconds
CONNECTION_TIMEOUT = 30 # Seconds
MAX_TX_COUNT = 20 # Max messages to send at once


class AjaxTransport (Transport):
  """
  Messenger transport for Messenger Over JSON-RPC Over HTTP.
  """
  def __init__ (self, nexus = None):
    Transport.__init__(self, nexus)
    self._connections = {}
    self._t = Timer(SESSION_TIMEOUT, self._check_timeouts, recurring=True)

  def _check_timeouts (self):
    pass

  def _forget (self, connection):
    # From Transport
    if connection._session_id in self._connections:
      del self._connections[connection._session_id]
    else:
      #print "Failed to forget", connection
      pass

  def create_session (self):
    pass

  def get_session (self, key):
    pass


def _result (m):
  pass


class AjaxConnection (Connection):
  """
  Messenger connection for Messenger Over JSON-RPC Over HTTP.

  Note: The sequence numbers used by this module simply increment and
        never wrap.  This should mean like nine quadrillion, but it
        depends on your browser and I definitely haven't tested this. :)
  """
  def __init__ (self, transport):
    Connection.__init__(self, transport)
    self._cond = threading.Condition()
    self._quitting = False

    # We're really protected from attack by the session key, we hope, so
    # we currently start tx_seq at zero, which makes it easier for the
    # client.
    self._next_tx_seq = 0  # next seq to create
    self._sent_tx_seq = -1 # last seq sent
    self._rx_seq = None

    # Waiting outgoing messages as (seq, msg) pairs
    self._tx_buffer = []

    # Out-of-order messages we've gotten (the in-order ones are dispatched
    # immediately, so they're never buffered)
    self._rx_buffer = []

    self._touch()

    self._send_welcome()

  def _touch (self):
    self._touched = time.time()

  def _check_timeout (self):
    pass

  def _close (self):
    super(AjaxConnection, self)._close()
    #TODO: track request sockets and cancel them?
    self._quitting = True

  def send (self, data):
    if self._is_connected is False: return False
    self._cond.acquire()
    self._tx_buffer.append((self._next_tx_seq, data))
    self._next_tx_seq += 1
    self._cond.notify()
    self._cond.release()

  def _get_tx_batch (self, seq, batch_size = None):
    """
    Returns the next batch of messages to send
    """
    pass

  def tx (self, wfile, seq, batch_size):
    """
    Sends outgoing messages to a waiting client.

    Can block long-polling style for a while to wait
    until it has some to send.
    """
    pass

  def rx (self, msg, seq):
    """
    Receive a message (or more than one) from RPC
    """
    pass


class AjaxMsgHandler (JSONRPCHandler):
  """
  Handles JSON-RPC messages from webcore for messenger.
  """

  def _exec_stop (self, session_id):
    """
    End a session

    You can always just stop and wait for it to time out, but this is nice
    if you can swing it.
    """
    pass

  def _exec_send (self, session_id, msg, seq = None):
    """
    Send a message (or messages)

    If seq is specified, it is a sequence number.  This can help
    eliminate problems with ordering.
    """
    pass

  def _exec_poll (self, session_id, seq = None, batch_size = None):
    """
    Get waiting messages

    If seq is specified, it is the sequence number of the first
    message you want.  This acks all previous messages.
    If batch_size is specified, it is how many messages you want.
    """
    pass

  def _get_session (self, key, create = True):
    pass


def launch (username='', password=''):
  pass
