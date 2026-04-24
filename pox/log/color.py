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

# NOTE: Not platform independent -- uses VT escape codes

# Magic sequence used to introduce a command or color
MAGIC = "@@@"

# Colors for log levels
LEVEL_COLORS = {
  'DEBUG': 'CYAN',
  'INFO': 'GREEN',
  'WARNING': 'YELLOW',
  'ERROR': 'RED',
  'CRITICAL': 'blink@@@RED',
}

# Will get set to True if module is initialized
enabled = False

# Gets set to True if we should strip special sequences but
# not actually try to colorize
_strip_only = False

import logging
import sys

# Name to (intensity, base_value) (more colors added later)
COLORS = {
 'black' : (0,0),
 'red' : (0,1),
 'green' : (0,2),
 'yellow' : (0,3),
 'blue' : (0,4),
 'magenta' : (0,5),
 'cyan' : (0,6),
 'gray' : (0,7),
 'darkgray' : (1,0),
 'pink' : (1,1),
 'white' : (1,7),
}

# Add intense/bold colors (names it capitals)
for _c in [_n for _n,_v in list(COLORS.items()) if _v[0] == 0]:
  COLORS[_c.upper()] = (1,COLORS[_c][1])

COMMANDS = {
  'reset' : 0,
  'bold' : 1,
  'dim' : 2,
  'bright' : 1,
  'dull' : 2,
  'bright:' : 1,
  'dull:' : 2,
  'blink' : 5,
  'BLINK' : 6,
  'invert' : 7,
  'bg:' : -1, # Special
  'level' : -2, # Special -- color of current level
  'normal' : 22,
  'underline' : 4,
  'nounderline' : 24,
}


# Control Sequence Introducer
CSI = "\033["

def _color (color, msg):
  """ Colorizes the given text """
  pass

def _proc (msg, level_color = "DEBUG"):
  """
  Do some replacements on the text
  """
  pass


def launch (entire=False):
  """
  If --entire then the whole message is color-coded, otherwise just the
  log level.

  Also turns on interpretation of some special sequences in the log
  format string.  For example, try:
   log --format="%(levelname)s: @@@bold%(message)s@@@normal" log.color
  """
  pass
