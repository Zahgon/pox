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
Dumps info about switches when they first connect
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str

log = core.getLogger()

# Formatted switch descriptions we've logged
# (We rememeber them so that we only print them once)
_switches = set()

# .. unless always is True in which case we always print them
_always = False

def _format_entry (desc):
  pass

def _handle_ConnectionUp (event):
  pass

def _handle_SwitchDescReceived (event):
  pass


def launch (always = False):
  pass
