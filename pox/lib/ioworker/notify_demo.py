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
A demo of working with IOWorker clients and servers

Run the server as:
 lib.ioworker.notify_demo:server

Clients can be run in several ways...

To just listen for notifications and show them as log messages:
 lib.ioworker.notify_demo:client --server=127.0.0.1 --name=SirSpam

To send a notification and quit, append --msg="Spam eggs spam".

Run with the Python interpreter (the 'py' component), and you get a
notify("<message>") command:
 POX> notify("Grilled tomatoes")

Run with Tk (the 'tk' component) to get a GUI.
"""

from pox.lib.ioworker import *
from pox.lib.ioworker.workers import *
from pox.core import core

log = core.getLogger()


# ---------------------------------------------------------------------------
# Client Stuff
# ---------------------------------------------------------------------------

client_worker = None
username = None
single_message = None

def notify (msg):
  if msg is None: return
  if client_worker is None:
    log.error("Can't send notification -- not connected")
  msg = msg.split("\n")
  for m in msg:
    client_worker.send("N %s %s\n" % (username, m))

class ClientWorker (PersistentIOWorker):
  def __init__ (self, *args, **kw):
    self.data = b''
    super(ClientWorker,self).__init__(*args,**kw)

  def _handle_close (self):
    pass

  def _handle_connect (self):
    pass

  def _handle_rx (self):
    self.data += self.read()
    while '\n' in self.data:
      msg,self.data = self.data.split('\n',1)
      if msg.startswith("N "):
        _,name,content = msg.split(None,2)
        log.warn("** %s: %s **", name, content)
        if core.hasComponent('tk'):
          # If Tk is running, pop up the message.
          core.tk.dialog.showinfo("Message from " + name, content)


def setup_input ():
  pass


def client (server, name = "Unknown", port = 8111, msg = None):

  pass


# ---------------------------------------------------------------------------
# Server Stuff
# ---------------------------------------------------------------------------

class ServerWorker (TCPServerWorker, RecocoIOWorker):
  pass

clients = set()

class NotifyWorker (RecocoIOWorker):
  def __init__ (self, *args, **kw):
    super(NotifyWorker, self).__init__(*args, **kw)
    self._connecting = True
    self.data = b''

  def _handle_close (self):
    pass

  def _handle_connect (self):
    pass

  def _handle_rx (self):
    self.data += self.read()
    while '\n' in self.data:
      msg,self.data = self.data.split('\n',1)
      if msg.startswith("N "):
        _,name,content = msg.split(None,2)
        log.warn("** %s: %s **", name, content)
        for c in clients:
          if c is not self:
            c.send(msg + "\n")


def server (port = 8111):
  pass
