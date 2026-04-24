# Copyright 2018 James McCauley
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
Websocket request handler

The request handler is meant to be subclassed, and it plays nicely with
the cooperative context (you can call send() from the cooperative
context, and the override-friendly handler functions are called within
the cooperative context).

Subclasses are likely interested in overriding the _on_X() methods
(especially _on_message), and the send() and maybe disconnect() API
methods.

There's also a demonstration here which uses a websocket to send logs
to the browser and take a bit of log configuration from the browser.
Launch it with web.websocket:log_service.
"""

import socket
import threading

from pox.core import core

log = core.getLogger()

import base64
import hashlib
import struct
import json

from pox.web.webcore import SplitRequestHandler

from http.cookies import SimpleCookie

from collections import deque


class WebsocketHandler (SplitRequestHandler, object):
  """
  Websocket handler class

  New messages arriving from the browser are handed to _on_message(), which
  you can subclass.  This handler is called from the cooperative context.

  _on_start() and _on_stop() can be overridden and are called at the
  obvious times (hopefully).  Again, they're called cooperatively.

  You can send messages via send().  This should be called from the
  cooperative context.
  """

  # We always set no cookieguard, because this is what the split request
  # handler looks at, and we don't want *it* to do cookieguard.
  pox_cookieguard = False

  # This controls whether websockets actually do cookieguard.  If we
  # set it to None, the parent's (splitter's) value is used.
  ws_pox_cookieguard = None

  _websocket_open = False
  _initial_send_delay = 0.010
  _send_delay = 0
  _lock = None
  _pending = False
  _rx_queue = None

  # No longer optional. USE_LOCK = True
  READ_TIMEOUT = 5

  WS_CONTINUE = 0
  WS_TEXT = 1
  WS_BINARY = 2
  WS_CLOSE = 8
  WS_PING = 9
  WS_PONG = 10

  def log_message (self, format, *args):
    pass

  def _init (self):
    self._send_buffer = b''
    self._rx_queue = deque()
    if True: # No longer optional. self.USE_LOCK:
      self._lock = threading.RLock()

  def _serve_websocket (self):
    pass

    #log.debug("Websocket quit")

  def do_GET (self):
    # Compatible with AuthMixin
    pass

  def _queue_call (self, f):
    self._ws_message(None, f) # See note in _ws_message()

  def _ws_message (self, opcode, data):
    # It's a hack, but this is also used to push arbitrary function calls from
    # the WS thread to the cooperative context, by setting opcode as None and
    # the function as data.
    self._rx_queue.append((opcode,data))
    cl = True
    if self._lock:
      with self._lock:
        if self._pending:
          cl = False
        else:
          self._pending = True
    if cl: core.call_later(self._ws_message2)

  def _ws_message2 (self):
    pass

  @staticmethod
  def _frame (opcode, msg):
    def encode_len (l):
      if l <= 0x7d:
        return struct.pack("!B", l)
      elif l <= 0xffFF:
        return struct.pack("!BH", 0x7e, l)
      elif l <= 0x7FFFFFFFFFFFFFFF:
        return struct.pack("!BQ", 0x7f, l)
      else:
        raise RuntimeError("Bad length")

    op_flags = 0x80 | (opcode & 0x0F) # 0x80 = FIN
    hdr = struct.pack("!B", op_flags) + encode_len(len(msg))

    return hdr + msg

  def _send_real (self, msg):
    if self._send_buffer:
      self._send_buffer += msg
      return

    try:
      written = self.connection.send(msg)
      if written < len(msg):
        # Didn't send all of it.
        assert not self._send_buffer
        self._send_delay = self._initial_send_delay
        self._send_buffer = msg[written:]
        core.call_later(self._delayed_send)
    except Exception as e:
      self.disconnect()
      #TODO: reopen?

  def _delayed_send (self):
    pass
      #TODO: reopen?

  def __del__ (self):
    self.disconnect()


  # The following are useful for subclasses...
  @property
  def is_connected (self):
    pass

  def disconnect (self):
    if self._lock:
      with self._lock:
        if self._websocket_open is False:
          return False
        self._websocket_open = False
    elif self._websocket_open is False:
      return False
    self._websocket_open = False
    try:
      self._queue_call(self._on_stop)
    except Exception:
      log.exception("While disconnecting")
    try:
      self.connection.shutdown(socket.SHUT_RD)
    except socket.error as e:
      pass
    return True

  def send (self, msg):
    if isinstance(msg, dict): msg = json.dumps(msg)
    try:
      msg = self._frame(self.WS_TEXT, msg.encode())
      self._send_real(msg)
    except Exception as e:
      log.exception("While sending")
      self.disconnect()

  def _on_message (self, op, msg):
    """
    Called when a new message arrives

    Override me!
    """
    pass

  def _on_start (self):
    """
    Called when the Websocket is established

    Override me!
    """
    pass

  def _on_stop (self):
    """
    Called when the Websocket connection is lost

    Override me!
    """
    pass



class LogWebsocketHandler (WebsocketHandler):
  """
  Sends log messages to a websocket

  The browser can also send us JSON objects with logger_name:logger_levels
  to control logging levels.

  This is mostly meant as an example of WebsocketHandler.
  """
  log_handler = None

  import logging
  class WSLogHandler (logging.Handler):
    web_handler = None # Set externally
    def emit (self, record):
      pass

  def _on_message (self, op, msg):
    pass

  def _on_start (self):
    pass

  def _on_stop (self):
    pass



_log_page = """
<!DOCTYPE html>
<html>
<head>
<title>POX Log</title>
<script language="javascript" type="text/javascript">

function out (msg, color)
{
  var el = document.createElement("pre");
  if (color) el.style.cssText = "color:" + color + ";";
  el.innerHTML = msg;
  document.getElementById("output").appendChild(el);
  el.scrollIntoView();
}

function connect ()
{
  ws = new WebSocket("ws://SERVER_ADDRESS/wslog/ws");
  ws.onopen = function(e) { };
  ws.onclose = function(e) {
    out("<a onclick='connect()' style='color:red'>Disconnected - Click to"
        + " reconnect</a>", "red");
  };
  ws.onmessage = function(e) {
    out(e.data.replace("<","&lt;").replace(">","&gt;"));
  };
  ws.onerror = function(e) { out("Error " + e.data, "red"); };
}

function send_level ()
{
  var el = document.getElementById("level_box");
  var level = el.options[el.selectedIndex].text;
  if (level)
  {
    console.log("Change level to " + level);
    ws.send(JSON.stringify({"": level}));
    // Use "" as the logger name to get the root logger
  }
}

window.addEventListener("load", connect, false);

</script>
</head>
<body>
<h1><a href="help.txt">POX Log Page</a></h1>
Root Log Level: <select id="level_box" onchange="send_level()">
  <option></option>
  <option>ERROR</option>
  <option>WARNING</option>
  <option>INFO</option>
  <option>DEBUG</option>
</select>
<div id="output"></div>
</body>
</html>
"""

_log_help_page = """
Connecting to the base page should result in log messages being sent to the
browser via a websocket.

You can also send JSON objects from the browser over the websocket containing
key/value pairs of logger-name/logger-level.  For example:

{"core": "INFO", "web":"ERROR"}

The "Root Log Level" popup does exactly this for the root logger.

This is really just meant as a demonstration of the Websocket infrastructure.
(And it demonstrates InternalContentHandler a bit too.)
"""

def log_service ():
  """
  Sends log messages to a browser via websocket

  This is mostly just meant as a demonstration of websockets in POX.
  """
  pass
