# Copyright 2011 James McCauley
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

import logging
from logging.handlers import *

_formatter = logging.Formatter(logging.BASIC_FORMAT)

def _parse (s):
  pass


#NOTE: Arguments are not parsed super-intelligently.  The result is that some
#      cases will be wrong (i.e., filenames that are only numbers or strings
#      with commas).  But I think this should be usable for most common cases.
#      You're welcome to improve it.

def launch (__INSTANCE__ = None, **kw):
  """
  Allows you to configure log handlers from the commandline.

  Examples:
   ./pox.py log --file=pox.log,w --syslog --no-default
   ./pox.py log --*TimedRotatingFile=filename=foo.log,when=D,backupCount=5

  The handlers are most of the ones described in Python's logging.handlers,
  and the special one --no-default, which turns off the default logging to
  stderr.

  Arguments are passed positionally by default.  A leading * makes them pass
  by keyword.

  If a --format="<str>" is specified, it is used as a format string for a
  logging.Formatter instance for all loggers created with that invocation
  of the log module.  If no loggers are created with this instantiation,
  it is used for the default logger.
  If a --format is specified, you can also specify a --datefmt="<str>"
  where the string is a strftime format string for date/time stamps.
  """
  pass
