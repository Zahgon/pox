# Copyright 2012,2013 James McCauley
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
Creates a spanning tree.

This component uses the discovery component to build a view of the network
topology, constructs a spanning tree, and then disables flooding on switch
ports that aren't on the tree by setting their NO_FLOOD bit.  The result
is that topologies with loops no longer turn your network into useless
hot packet soup.

This component is inspired by and roughly based on the description of
Glenn Gibb's spanning tree module for NOX:
  http://www.openflow.org/wk/index.php/Basic_Spanning_Tree

Note that this does not have much of a relationship to Spanning Tree
Protocol.  They have similar purposes, but this is a rather different way
of going about it.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from collections import defaultdict
from pox.openflow.discovery import Discovery
from pox.lib.util import dpidToStr
from pox.lib.recoco import Timer
import time

log = core.getLogger()

# Might be nice if we made this accessible on core...
#_adj = defaultdict(lambda:defaultdict(lambda:[]))

def _calc_spanning_tree ():
  """
  Calculates the actual spanning tree

  Returns it as dictionary where the keys are DPID1, and the
  values are tuples of (DPID2, port-num), where port-num
  is the port on DPID1 connecting to DPID2.
  """
  pass


# Keep a list of previous port states so that we can skip some port mods
# If other things mess with port states, these may not be correct.  We
# could also refer to Connection.ports, but those are not guaranteed to
# be up to date.
_prev = defaultdict(lambda : defaultdict(lambda : None))

# If True, we set ports down when a switch connects
_noflood_by_default = False

# If True, don't allow turning off flood bits until a complete discovery
# cycle should have completed (mostly makes sense with _noflood_by_default).
_hold_down = False


def _handle_ConnectionUp (event):
  # When a switch connects, forget about previous port states
  pass


def _handle_LinkEvent (event):
  # When links change, update spanning tree

  pass


def _update_tree (force_dpid = None):
  """
  Update spanning tree

  force_dpid specifies a switch we want to update even if we are supposed
  to be holding down changes.
  """
  pass


_dirty_switches = {} # A map dpid_with_dirty_ports->Timer
_coalesce_period = 2 # Seconds to wait between features requests

def _invalidate_ports (dpid):
  """
  Registers the fact that port info for dpid may be out of date

  When the spanning tree adjusts the port flags, the port config bits
  we keep in the Connection become out of date.  We don't want to just
  set them locally because an in-flight port status message could
  overwrite them.  We also might not want to assume they get set the
  way we want them.  SO, we do send a features request, but we wait a
  moment before sending it so that we can potentially coalesce several.

  TLDR: Port information for this switch may be out of date for around
        _coalesce_period seconds.
  """
  pass

def _check_ports (dpid):
  """
  Sends a features request to the given dpid
  """
  pass


def launch (no_flood = False, hold_down = False):
  pass
