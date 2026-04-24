# Copyright 2017,2018 James McCauley
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
Loads a config file

Config files have a format like:
  [module_name]
  # A comment line
  flag_argument
  argument_with_value=42
  argument_using_variable=My name is ${name}.
  !special_directive

Special directives include:
  !ignore       Ignore this whole module (easier than commenting it out).
                You can also do "!ignore [true|false]".
  !append       Append arguments to previous module definition instead of
                a new instance of this module
  !set foo=bar  Set variable foo to 'bar' (or just !set for True)
  !unset foo    Unset variable foo
  !gset foo=bar Set global variable foo to 'bar'
  !gunset foo   Unset global variable foo
  [!include x]  Include another config file named 'x' (See below)
  !log[=lvl] .. Log the rest of the line at the given level (or INFO)

You can also do things conditionally depending on whether a variable is
set or not using !ifdef/!elifdef/!ifndef/!elifndef/!else/!endif.

Config file values can have variables set with config.var and referenced
with, e.g., "${var_name}".  For the above, you might use:
  config.var --name=Jane
or
  config.gvar --name=Jane
The difference is that the former is only valid for the next config file
processed.  The latter stays valid for all subsequent config files.

The following special variables are available:
 _CONFIG_DIR_    The directory of the config file being processed.
 _CURRENT_DIR_   The current working directory.
 _POXCORE_DIR_   The directory of pox.core.
"""

from pox.config.var import variables
from pox.config.gvar import gvariables
from pox.boot import _do_launch #TODO: Make this public
from pox.lib.util import str_to_bool
import pox as pox_base
import os


class LogError (RuntimeError):
  pass



def _var_sub (v, allow_bool=False):
  pass


def _handle_var_set (line, vs):
  pass


def _handle_var_unset (line, vs):
  pass



class IfStack (object):
  def __init__ (self):
    self.stack = [1] # 0 = Unmatched, 1 = Matches-Current, 2 = Done-Matching
    # We start off with 1 as if we were always in an "if True"

  def start_if (self):
    pass

  def set_match (self, matches=True):
    pass

  @property
  def can_execute (self):
    pass

  def end_if (self, cmd):
    pass

  def finish (self):
    pass



def _careful_set (d, k, v):
  pass



def launch (file, __INSTANCE__=None):
  pass
