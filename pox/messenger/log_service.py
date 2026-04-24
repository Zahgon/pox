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
This is a messenger service for working with the log.

It does two things:
  a) Listen on the "log" channel.  You can send messages to this
     channel with keys lowerLevels/RaiseLevels/setLevels to adjust
     global log levels.  See _process_commands() for more info.
  b) You can join any channel named log_<something> (your session
     ID is a good choice for the something), and a LogBot will
     join it.  This will result in receiving log messages.  In
     your join message (or afterwards), you can configure levels,
     the message formats, etc.  See LogService for more details.
"""

from pox.core import core
from pox.messenger import *
from pox.lib.revent.revent import autoBindEvents
import logging
import traceback

log = core.getLogger()

# These attributes are copied verbatim from the log record
_attributes = [
  'created','filename','funcName','levelname','levelno','lineno',
  'module','msecs','name','pathname','process','processName',
  'relativeCreated','thread','threadName','args',
]


class LogFilter (object):
  """
  Filters messages from the web server component

  It's a nasty situation when you're using the HTTP messenger transport
  to view the log when in debug mode, as every webserver log message
  creates a messenger message which creates a webserver message, ...

  This just turns off debug messages from the webserver.
  """
  def filter (self, record):
    pass


class LogHandler (logging.Handler):
  """
  A Python logging.Handler for the messenger

  Accepts dictionaries with configuration info:
  KEY            VALUE
  level          Minimum log level to output (probably one of CRITICAL,
                 ERROR, WARNING, INFO or DEBUG)
  format         fmt argument to logging.Formatter
  dateFormat     datefmt argument to logging.Formatter
  json           true if you want a bunch of attributes from the LogRecord to
                 be included.  In some cases these are stringized since  the
                 originals are objects and we don't pickle/jsonpickle them.
  subsystems     A list of logger names to listen to.  A "null"/None entry in
                 the list means the root logger (which is also the default).
  add_subsystems A list of ADDITIONAL subsystems to listen to.
  """
  #NOTE: We take advantage of the fact that the default value for the
  #      argument to getLogger() is None.  This is currently true, but
  #      isn't documented, so it might change in the future (though I
  #      don't see why it would!).  Doing this "the right way" results
  #      in much uglier code.

  def __init__ (self, channel, params):
    logging.Handler.__init__(self)
    self._channel = channel
    self.addFilter(LogFilter())
    self._json = False
    self._format = False # Not valid, should never be set
    self._dateFormat = None
    self.subsystems = []
    if "format" not in params:
      params["format"] = None # Force update
    if 'subsystems' not in params:
      self._add_subsystems([None])

    self._process_parameters(params)

  def _add_subsystems (self, subsystems):
    """
    Add log subsystems to listen to
    """
    for subsystem in subsystems:
      if subsystem in self.subsystems: continue
      try:
        logging.getLogger(subsystem).addHandler(self)
        self.subsystems.append(subsystem)
      except:
        pass

  def _drop_subsystems (self):
    """
    Stop listening to all log subsystems
    """
    for subsystem in self.subsystems:
      logging.getLogger(subsystem).removeHandler(self)
    self.subsystems = []

  def _process_parameters (self, params):
    if "level" in params:
      self.setLevel(params["level"])
    if "subsystems" in params:
      self._drop_subsystems()
      self._add_subsystems(params['subsystems'])
    if 'add_subsystems' in params:
      self._add_subsystems(params['add_subsystems'])
    if 'remove_subsystems' in params:
      #TODO
      log.error('remove_subsystems unimplemented')
    if "json" in params:
      self._json = params['json']
    if "setLevels" in params:
      levels = params['setLevels']
      if isinstance(levels, dict):
        for k,v in levels.items():
          l = core.getLogger(k)
          l.setLevel(v)
      else:
        core.getLogger().setLevel(levels)

    doFormat = False
    if "format" in params:
      fmt = params['format']
      if fmt is not self._format:
        self._format = fmt
        doFormat = True
    if "dateFormat" in params:
      dateFormat = params['dateFormat']
      if dateFormat is not self._dateFormat:
        self._dateFormat = dateFormat
        doFormat = True

    if doFormat:
      self.setFormatter(logging.Formatter(self._format, self._dateFormat))

  def _close (self):
    self._drop_subsystems()

  def emit (self, record):
    pass


def _process_commands (msg):
  """
  Processes logger commands
  """
  def get (key):
    r = msg.get(key)
    if r is not None:
      if not isinstance(r, dict):
        r = {None:r}
    else:
      return {}
    return r

  lowerLevels = get("lowerLevels") # less verbose
  raiseLevels = get("raiseLevels") # more verbose
  setLevels = get("setLevels")

  for k,v in lowerLevels.items():
    logger = core.getLogger(k)
    level = logging._checkLevel(v)
    if not l.isEnabledFor(level+1):
      logger.setLevel(v)

  for k,v in raiseLevels.items():
    logger = core.getLogger(k)
    if not l.isEnabledFor(v):
      logger.setLevel(v)

  for k,v in setLevels.items():
    logger = core.getLogger(k)
    logger.setLevel(v)

  message = msg.get("message", None)
  if message:
    level = msg.get("level", "DEBUG")
    if isinstance(level, str):
      import logging
      if not level.isalpha():
        level = logging.DEBUG
      else:
        level = level.upper()
        level = getattr(logging, level, logging.DEBUG)
    sub = msg.get("subsystem", "<external>")
    logging.getLogger(sub).log(level, message)


class LogBot (ChannelBot):
  def _init (self, extra):
    self._handler = None

  def _join (self, event, con, msg):
    #self.reply(event, hello = "Hello, %s!" % (con,))
    pass

  def _leave (self, con, empty):
    pass

  def _unhandled (self, event):
    _process_commands(event.msg)
    self._handler._process_parameters(event.msg)


def _handle_new_channel (event):
  pass

def launch (nexus = "MessengerNexus"):
  pass
