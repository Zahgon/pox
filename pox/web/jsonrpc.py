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
A library for implementing JSON-RPC based web services

This is lightweight, low on features, and not a whole lot of effort
has been paid to really complying with the JSON-RPC spec.  Feel
free to improve it. ;)

It'd be nice to factor the JSON-RPC stuff out so that it could
be used with something besides just HTTP.

Also, it has some capability for compatibility with Qooxdoo.

See the openflow.webservice component for an example.

IMPORTANT NOTE:
Per the specifiction, JSON-RPC requests without an "id" field are
*notifications* which do not require and should not receive responses.
In other words, if you want to get a reply to a request, you must
include an "id" member in the request.  You can, for example, just
set it to 1 if you don't have anything better to set it to.
"""

import json
import sys
from pox.web.webcore import *
from pox.core import core
log = core.getLogger()


# A long polling handler can return this if it notices that the
# connection has closed.
ABORT = object()


class JSONRPCHandler (SplitRequestHandler):
  """
  Meant for implementing JSON-RPC web services

  Implement RPC methods by prefacing them with "_exec_".

  config keys of note:
   "auth" is a function which takes a username and password and returns
       True if they are a valid user.  If set, turns on authentication.
   "auth_realm" is the optional authentication realm name.
   "qx" turns on Qooxdoo mode by default (it's usually switched on by
       seeing a "service" key in the request).

  There are a couple of extensions to JSON-RPC:

  If you want to use positional AND named parameters, in a request, use
  "params" for the former and "kwparams" for the latter.

  There's an optional "service" key in requests.  This comes from qooxdoo.
  If it is given, look for the _exec_ method on some otherobject instead
  of self.  Put the additional services in an arg named 'services'.
  """
  protocol_version = 'HTTP/1.1'

  QX_ERR_ILLEGAL_SERVICE = 1
  QX_ERR_SERVICE_NOT_FOUND = 2
  QX_ERR_CLASS_NOT_FOUND = 3
  QX_ERR_METHOD_NOT_FOUND = 4
  QX_ERR_PARAMETER_MISMATCH = 5
  QX_ERR_PERMISSION_DENIED = 6

  QX_ORIGIN_SERVER = 1
  QX_ORIGIN_METHOD = 2

  ERR_PARSE_ERROR = -32700             # WE USE THIS
  ERR_INVALID_REQUEST = -32600
  ERR_METHOD_NOT_FOUND = -32601        # WE USE THIS
  ERR_INVALID_PARAMS = -32602
  ERR_INTERNAL_ERROR = -32603          # WE USE THIS
  ERR_SERVER_ERROR = -32000 # to -32099  WE USE THIS

  ERR_METHOD_ERROR = 99 # We use this for errors in methods

  ERROR_XLATE = {
    ERR_PARSE_ERROR      : (1, QX_ERR_ILLEGAL_SERVICE), # Nonsense
    ERR_METHOD_NOT_FOUND : (1, QX_ERR_METHOD_NOT_FOUND),
    ERR_INTERNAL_ERROR   : (),
    ERR_SERVER_ERROR     : (),
  }

  _qx = False

  def _init (self):
    # Maybe the following arg-adding feature should just be part of
    # SplitRequestHandler?

    for k,v in self.args.items():
      setattr(self, "_arg_" + k, v)

    self.auth_function = self.args.get('auth', None)
    self.auth_realm = self.args.get('auth_realm', "JSONRPC")

    self._qx = self.args.get('qx', self._qx)

  def _send_auth_header (self):
    pass

  def _do_auth (self):
    pass

  def _translate_error (self, e):
    if not 'error' in e: return
    if self._qx:
      if e['code'] < 0:
        c,o = ERROR_XLATE.get(e['code'], (1, self.QX_ERR_ILLEGAL_SERVICE))
        e['code'] = c
        e['origin'] = o
      else:
        e['origin'] = QX_ORIGIN_METHOD

  def _handle (self, data):
    pass

  def do_POST (self):
    pass


class QXJSONRPCHandler (JSONRPCHandler):
  """
  A subclass of JSONRPCHandler which speaks something closer to
  qooxdoo's version JSON-RPC.
  """
  _qx = True
  #TODO: Implement the <SCRIPT> based GET method for cross-domain


def make_error (msg = "Unknown Error",
                code = JSONRPCHandler.ERR_SERVER_ERROR,
                data = None):
  e = {'code':code,'message':msg}
  if data is not None:
    e['data'] = data
  r = {'error':e}
  return r
