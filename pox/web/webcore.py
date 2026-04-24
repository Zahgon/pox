# Copyright 2011,2012,2018 James McCauley
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
Webcore is a basic web server framework based on the SocketServer-based
BaseHTTPServer that comes with Python.  The big difference is that this
one can carve up URL-space by prefix, such that "/foo/*" gets handled by
a different request handler than "/bar/*".  I refer to this as "splitting".

You should also be able to make a request handler written without splitting
run under Webcore.  This may not work for all request handlers, but it
definitely works for some. :)  The easiest way to do this is with the
wrapRequestHandler() function, like so:
  from CGIHTTPServer import CGIHTTPRequestHandler as CHRH
  core.WebServer.set_handler("/foo", wrapRequestHandler(CHRH))

.. now URLs under the /foo/ directory will let you browse through the
filesystem next to pox.py.  If you create a cgi-bin directory next to
pox.py, you'll be able to run executables in it.

For this specific purpose, there's actually a SplitCGIRequestHandler
which demonstrates wrapping a normal request handler while also
customizing it a bit -- SplitCGIRequestHandler shoehorns in functionality
to use arbitrary base paths.

BaseHTTPServer is not very fast and needs to run on its own thread.
It'd actually be great to have a version of this written against, say,
CherryPy, but I did want to include a simple, dependency-free web solution.
"""

from socketserver import ThreadingMixIn
from http.server import *
from time import sleep
import select
import threading

from .authentication import BasicAuthMixin

from pox.core import core
from pox.lib.revent import Event, EventMixin

import os
import socket
import posixpath
import urllib.request, urllib.parse, urllib.error
import cgi
import errno
from io import StringIO, BytesIO

log = core.getLogger()
try:
  weblog = log.getChild("server")
except:
  # I'm tired of people running Python 2.6 having problems with this.
  #TODO: Remove this someday.
  weblog = core.getLogger("webcore.server")

def _setAttribs (parent, child):
  attrs = ['command', 'request_version', 'close_connection',
           'raw_requestline', 'requestline', 'path', 'headers', 'wfile',
           'rfile', 'server', 'client_address', 'connection', 'request']
  for a in attrs:
    setattr(child, a, getattr(parent, a))

  setattr(child, 'parent', parent)



import weakref

class ShutdownHelper (object):
  """
  Shuts down sockets for reading when POX does down

  Modern browsers may open (or leave open) HTTP connections without sending
  a request for quite a while.  Python's webserver will open requests for
  these which will then just block at the readline() in handle_one_request().
  The downside here is that when POX tries to shut down, those threads are
  left hanging.  We could change things so that it didn't just blindly call
  and block on readline.  Or we could make the handler threads daemon threads.
  But instead, we just keep track of the sockets.  When POX wants to go down,
  we'll shutdown() the sockets for reading, which will get readline() unstuck
  and let POX close cleanly.
  """
  sockets = None
  def __init__ (self):
    core.add_listener(self._handle_GoingDownEvent)

  def _handle_GoingDownEvent (self, event):
    pass

  def register (self, socket, read=True, write=False, close=False):
    if self.sockets is None:
      self.sockets = weakref.WeakKeyDictionary()
    self.sockets[socket] = (read,write,close)

  def unregister (self, socket):
    if self.sockets is None: return
    try:
      del self.sockets[socket]
    except Exception as e:
      pass

_shutdown_helper = ShutdownHelper()



from http.cookies import SimpleCookie

POX_COOKIEGUARD_DEFAULT_COOKIE_NAME = "POXCookieGuardCookie"

def _gen_cgc ():
  #TODO: Use Python 3 secrets module
  import random
  import datetime
  import hashlib
  try:
    rng = random.SystemRandom()
  except Exception:
    log.error("Using insecure pseudorandom number for POX CookieGuard")
    rng = random.Random()
  data = "".join([str(rng.randint(0,9)) for _ in range(1024)])
  data += str(datetime.datetime.now())
  data += str(id(data))
  data = data.encode()
  return hashlib.sha256(data).hexdigest()


import urllib
from urllib.parse import quote_plus, unquote_plus

class POXCookieGuardMixin (object):
  """
  This is a CSRF mitigation we call POX CookieGuard.  This only stops
  CSRF with modern browsers, but has the benefit of not requiring
  requesters to do anything particularly special.  In particular, if you
  are doing something like using curl from the commandline to call JSON-RPCs,
  you don't need to do anything tricky like fetch an auth token and then
  include it in the RPC -- all you need is cookie support.  Basically this
  works by having POX give you an authentication token in a cookie.  This
  uses SameSite=Strict so that other sites can't convince the browser to
  send it.
  """

  _pox_cookieguard_bouncer = "/_poxcookieguard/bounce"
  _pox_cookieguard_secret = _gen_cgc()
  _pox_cookieguard_cookie_name = POX_COOKIEGUARD_DEFAULT_COOKIE_NAME
  _pox_cookieguard_consume_post = True

  def _cookieguard_maybe_consume_post (self):
    pass

  def _get_cookieguard_cookie (self):
    pass

  def _get_cookieguard_cookie_path (self, requested):
    """
    Gets the path to be used for the cookie
    """
    pass

  def _do_cookieguard_explict_continuation (self, requested, target):
    """
    Sends explicit continuation page
    """
    pass

  def _do_cookieguard_set_cookie (self, requested, bad_cookie):
    """
    Sets the cookie and redirects

    bad_cookie is True if the cookie was set but is wrong.
    """
    pass

  def _do_cookieguard (self, override=None):
    pass


import http.server
from http.server import SimpleHTTPRequestHandler


class SplitRequestHandler (BaseHTTPRequestHandler):
  """
  To write HTTP handlers for POX, inherit from this class instead of
  BaseHTTPRequestHandler.  The interface should be the same -- the same
  variables should be set, and the same do_GET(), etc. methods should
  be called.

  In addition, there will be a self.args which can be specified
  when you set_handler() on the server.
  """
  # Also a StreamRequestHandler

  def __init__ (self, parent, prefix, args):
    _setAttribs(parent, self)

    self.parent = parent
    self.args = args
    self.prefix = prefix

    self._init()

  def _init (self):
    """
    This is called by __init__ during initialization.  You can
    override it to, for example, parse .args.
    """
    pass

  @classmethod
  def format_info (cls, args):
    """
    Get an info string about this handler

    This is displayed, for example, in the "Web Prefixes" list of the default
    POX web server page.
    """
    pass

  def version_string (self):
    pass

  def handle_one_request (self):
    raise RuntimeError("Not supported")

  def handle(self):
    raise RuntimeError("Not supported")

  def _split_dispatch (self, command, handler = None):
    pass

  def log_request (self, code = '-', size = '-'):
    pass

  def log_error (self, fmt, *args):
    pass

  def log_message (self, fmt, *args):
    pass


_favicon = ("47494638396110001000c206006a5797927bc18f83ada9a1bfb49ceabda"
 + "4f4ffffffffffff21f904010a0007002c000000001000100000034578badcfe30b20"
 + "1c038d4e27a0f2004e081e2172a4051942abba260309ea6b805ab501581ae3129d90"
 + "1275c6404b80a72f5abcd4a2454cb334dbd9e58e74693b97425e07002003b")
_favicon = bytes(int(_favicon[n:n+2],16)
                 for n in range(0,len(_favicon),2))

class CoreHandler (SplitRequestHandler):
  """
  A default page to say hi from POX.
  """
  def do_GET (self):
    """Serve a GET request."""
    pass

  def do_HEAD (self):
    """Serve a HEAD request."""
    pass

  def do_content (self, is_get):
    pass

  def send_favicon (self, is_get = False):
    pass

  def send_info (self, is_get = False):
    pass


class StaticContentHandler (SplitRequestHandler, SimpleHTTPRequestHandler):
  """
  A SplitRequestHandler for serving static content

  This is largely the same as the Python SimpleHTTPRequestHandler, but
  we modify it to serve from arbitrary directories at arbitrary
  positions in the URL space.
  """

  server_version = "StaticContentHandler/1.0"

  def send_head (self):
    # We override this and handle the directory redirection case because
    # we want to include the per-split prefix.
    pass

  def list_directory (self, dirpath):
    # dirpath is an OS path
    pass

  def translate_path (self, path, include_prefix = True):
    """
    Translate a web-path to a local filesystem path

    Odd path elements (e.g., ones that contain local filesystem path
    separators) are stripped.
    """
    pass


def wrapRequestHandler (handlerClass):
  pass


from http.server import CGIHTTPRequestHandler
class SplitCGIRequestHandler (SplitRequestHandler,
                              CGIHTTPRequestHandler, object):
  """
  Runs CGIRequestHandler serving from an arbitrary path.
  This really should be a feature of CGIRequestHandler and the way of
  implementing it here is scary and awful, but it at least sort of works.
  """
  __lock = threading.Lock()
  def _split_dispatch (self, command):
    pass


class SplitterRequestHandler (BaseHTTPRequestHandler, BasicAuthMixin,
                              POXCookieGuardMixin):
  basic_auth_info = {} # username -> password
  basic_auth_enabled = None
  pox_cookieguard = True

  def __init__ (self, *args, **kw):
    if self.basic_auth_info:
      self.basic_auth_enabled = True

    #self.rec = Recording(args[0])
    #self.args = args
    #self.matches = self.matches.sort(key=lambda e:len(e[0]),reverse=True)
    #BaseHTTPRequestHandler.__init__(self, self.rec, *args[1:], **kw)
    try:
      BaseHTTPRequestHandler.__init__(self, *args, **kw)
    except socket.error as e:
      if e.errno == errno.EPIPE:
        weblog.warn("Broken pipe (unclean client disconnect?)")
      else:
        raise
    finally:
      _shutdown_helper.unregister(self.connection)

  def log_request (self, code = '-', size = '-'):
    pass

  def log_error (self, fmt, *args):
    pass

  def log_message (self, fmt, *args):
    pass

  def version_string (self):
    pass

  def _check_basic_auth (self, user, password):
    pass

  def _get_auth_realm (self):
    pass

  def handle_one_request(self):
    pass


class WebRequest (Event):
  """
  Hook for requests on the POX web server.

  This event is fired when the webserver is going to handle a request.
  The listener can modify the .handler to change how the event is
  handled.  Or it can just be used to spy on requests.

  If the handler is the splitter itself, then the page wasn't found.
  """
  splitter = None
  handler = None

  def __init__ (self, splitter, handler):
    self.splitter = splitter
    self.handler = handler

  def set_handler (self, handler_class):
    """
    Set a new handler class
    """
    h = self.handler
    self.handler = handler_class(h.parent, h.prefix, h.args)


class SplitThreadedServer(ThreadingMixIn, HTTPServer, EventMixin):
  _eventMixin_events = set([WebRequest])

  matches = [] # Tuples of (Prefix, TrimPrefix, Handler)

  def __init__ (self, *args, **kw):
    self.matches = list(self.matches)
    self.ssl_server_key = kw.pop("ssl_server_key", None)
    self.ssl_server_cert = kw.pop("ssl_server_cert", None)
    self.ssl_client_certs = kw.pop("ssl_client_certs", None)
    HTTPServer.__init__(self, *args, **kw)
#    self.matches = self.matches.sort(key=lambda e:len(e[0]),reverse=True)

    self.ssl_enabled = False
    if self.ssl_server_key or self.ssl_server_cert or self.ssl_client_certs:
      import ssl
      # The Python SSL stuff being used this way means that failing to set up
      # SSL can hang a connection open, which is annoying if you're trying to
      # shut down POX.  Do something about this later.
      cert_reqs = ssl.CERT_REQUIRED
      if self.ssl_client_certs is None:
        cert_reqs = ssl.CERT_NONE
      self.socket = ssl.wrap_socket(self.socket, server_side=True,
          keyfile = self.ssl_server_key, certfile = self.ssl_server_cert,
          ca_certs = self.ssl_client_certs, cert_reqs = cert_reqs,
          do_handshake_on_connect = True,
          ssl_version = ssl.PROTOCOL_TLSv1_2,
          suppress_ragged_eofs = True)
      self.ssl_enabled = True

  def set_handler (self, prefix, handler, args = None, trim_prefix = True):
    # Not very efficient
    assert (handler is None) or (issubclass(handler, SplitRequestHandler))
    self.matches = [m for m in self.matches if m[0] != prefix]
    if handler is None: return
    self.matches.append((prefix, handler, trim_prefix, args))
    self.matches.sort(key=lambda e:len(e[0]),reverse=True)

  def add_static_dir (self, www_path, local_path=None, relative=False):
    """
    Serves a directory of static content.
    www_path is the prefix of the URL that maps to this directory.
    local_path is the directory to serve content from.  If it's not
    specified, it is assume to be a directory with the same name as
    www_path.
    relative, if True, means that the local path is to be a sibling
    of the calling module.
    For an example, see the launch() function in this module.
    """
    pass


class InternalContentHandler (SplitRequestHandler):
  """
  Serves data from inside the application, without backing files

  When it receives a GET or a HEAD, it translates the path from something
  like "/foo/bar.txt" to "foo__bar_txt".  It then tries several things:
  1) Looking up an attribute on the handler called "GET_foo__bar_txt".
  2) Treating self.args as a dictionary and looking for
     self.args["/foo/bar.txt"].
  3) Looking on self.args for an attribute called "GET_foo__bar_txt".
  4) Looking up an attribute on the handler called "GETANY".
  5) Looking up the key self.args[None].
  6) Looking up the attribute "GETANY" on self.args.

  Whichever of these it gets, it the result is callable, it calls it,
  passing the request itself as the argument (so if the thing is a
  method, it'll essentially just be self twice).

  The attribute or return value is ideally a tuple of (mime-type, bytes,
  headers).  You may omit the headers.  If you include it, it can either
  be a dictionary or a list of name/value pairs.  If you return a string
  or bytes instead of such a tuple, it'll try to guess between HTML or
  plain text.  It'll then send that to the client.  Easy!

  When a handler is set up with set_handler(), the third argument becomes
  self.args on the request.  So that lets you put data into an
  InternalContentHandler without subclassing.  Or just subclass it.

  For step 2 above, it will also look up the given path plus a slash.  If
  it finds it, it'll do an HTTP redirect to it.  In this way, you can
  provide things which look like directories by including the slashed
  versions in the dictionary.
  """
  args_content_lookup = True # Set to false to disable lookup on .args

  def do_GET (self):
    pass
  def do_HEAD (self):
    pass

  def do_response (self, is_get):
    pass


class FileUploadHandler (SplitRequestHandler):
  """
  A default page to say hi from POX.
  """
  def do_GET (self):
    """Serve a GET request."""
    pass

  def do_HEAD (self):
    """Serve a HEAD request."""
    pass

  def send_form (self, is_get = False, msg = None):
    pass

  def do_POST (self):
    pass

  def on_upload (self, filename, datafile):
    pass


def upload_test (save=False):
  """
  Launch a file upload test

  --save will save the file using its MD5 for the filename
  """
  pass


def launch (address='', port=8000, static=False, ssl_server_key=None,
            ssl_server_cert=None, ssl_client_certs=None,
            no_cookieguard=False):
  """
  Starts a POX webserver

  --ssl_client_certs are client certificates which the browser supplies
    basically in order to authorize the client.  This is much more
    secure than just using HTTP authentication.

  --static alone enables serving static content from POX's www_root
    directory.  Otherwise it is a comma-separated list of prefix:paths
    pairs to serve (that is, it will serve the path at the prefix.  If
    there is no colon, it assumes the path and prefix are the same.  If
    one of the pairs is empty, we'll also serve www_root.

  --no-cookieguard disables POX CookieGuard.  See POXCookieGuardMixin
    documentation for more on this, but the short story is that disabling
    it will make your server much more vulnerable to CSRF attacks.
  """
  pass
