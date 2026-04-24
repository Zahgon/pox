# Copyright 2013 James McCauley
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
Simple datapath control framework for POX datapaths
"""

from pox.core import core
from pox.lib.ioworker.workers import *
from pox.lib.ioworker import *
from pox.lib.revent import *


# IOLoop for our IO workers
_ioloop = None

# Log
log = None


class CommandEvent (Event):
  """
  Event fired whenever a command is received
  """
  def __init__ (self, worker, cmd):
    super(CommandEvent,self).__init__()
    self.worker = worker
    self.cmd = cmd

  @property
  def first (self):
    pass

  @property
  def args (self):
    pass

  def __str__ (self):
    return "<%s: %s>" % (self.worker, self.cmd)


class ServerWorker (TCPServerWorker, RecocoIOWorker):
  """
  Worker to accept connections
  """
  pass
  #TODO: Really should just add this to the ioworker package.


class Worker (RecocoIOWorker):
  """
  Worker to receive POX dpctl commands
  """
  def __init__ (self, *args, **kw):
    super(Worker, self).__init__(*args, **kw)
    self._connecting = True
    self._buf = b''

  def _process (self, data):
    self._buf += data
    while '\n' in self._buf:
      fore,self._buf = self._buf.split('\n', 1)
      core.ctld.raiseEventNoErrors(CommandEvent, self, fore)


  def _handle_rx (self):
    self._buf += self.read()
    self._process(self.read())

  def _exec (self, msg):
    pass


class Server (EventMixin):
  """
  Listens on a TCP socket for control
  """
  _eventMixin_events = set([CommandEvent])

  def __init__ (self, port = 7791):
    self.port = port
    w = ServerWorker(child_worker_type=Worker, port = port)
    self.server_worker = w
    _ioloop.register_worker(w)


def create_server (port = 7791):
  # Set up logging
  pass


def server (port = 7791):
  pass


def launch (cmd, address = None, port = 7791):
  pass
