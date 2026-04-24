# Copyright 2017 James McCauley
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
Creates a spanning tree (or possibly more than one)

This component uses the discovery component to build a view of the network
topology, constructs a spanning tree, and then disables flooding on switch
ports that aren't on the tree by setting their NO_FLOOD bit.  The result
is that topologies with loops no longer turn your network into useless
hot packet soup.

Note that this does not have much of a relationship to Spanning Tree
Protocol.  They have similar purposes, but this is a rather different way
of going about it.

This component is intended to replace the spanning_tree component, but
it currently has no support for dynamic topologies (that is, where
something that used to be connected to one thing now connects to
another thing) and has fairly different behavior in general, so we
still have the spanning_tree module too (for now).
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.recoco import Timer
import time

log = core.getLogger()

def _now ():
  return time.time()



class Port (object):
  def __init__ (self, no, up):
    assert no < of.OFPP_MAX
    self.no = no
    self.up = up
    self.reset_wait()
    self.never_block = False

  def reset_wait (self):
    self.ts = _now()

  @property
  def waiting (self):
    # We'd like to wait for a while here, but it seems like NO_FWD
    # now affects sending packet_outs, which I don't think it used
    # to.  So waiting actually kills discovery.  So we only wait
    # a little while, hoping that it'll be enough to stop any
    # worst case behavior.
    pass

  @property
  def age (self):
    pass



def is_down (p):
  pass

def is_up (p):
  pass



class Switch (object):
  def __init__ (self, master, dpid):
    self.dpid = dpid
    self.log = log.getChild(dpid_to_str(dpid))
    self.ports = {}
    self._port_out_cache = None
    self._port_out = None
    self.master = master

  def get_port (self, p):
    pass

  def _handle_ConnectionUp (self, e):
    # Not a real event handler -- we call it ourselves
    pass

  def _handle_ConnectionDown (self, e):
    pass

  def _handle_PortStatus (self, e):
    pass

  def _handle_timer (self):
    pass

  def _sync_port_data (self):
    # Make sure we've got the latest port info
    pass

  def _compute (self):
    pass

  def _realize (self):
    pass

  def send (self, data):
    con = core.openflow.connections.get(self.dpid)
    if not con:
      self.log.info("Not connected -- didn't send %s bytes" % (len(data),))
      return False
    con.send(data)
    return True



class LinkData (object):
  def __init__ (self, link):
    self.link = link.uni
    self.uv_ts = 0.0 # Long time ago!
    self.vu_ts = 0.0 # Long time ago!
    assert self.link.end[0][0] != self.link.end[1][0] # Unsupported
    self.on_tree = False

  @property
  def up (self):
    pass

  @property
  def forward_up (self):
    pass

  @property
  def reverse_up (self):
    pass

  @property
  def liveness (self):
    # 0 -> down, 1 -> up, 0.5 -> half up
    pass

  def mark_alive (self, link):
    pass

  def mark_dead (self, link = None):
    pass

  def port (self, sw):
    pass

  def otherport (self, sw):
    pass

  def pair (self, sw):
    pass

  def otherpair (self, sw):
    pass

  def __hash__ (self):
    return hash(self.link)

  def __cmp__ (self, other):
    if isinstance(other, LinkData):
      return cmp(self.link, other.link)
    raise RuntimeError("Bad comparison") # Don't do this



class Topo (object):
  def __init__ (self):
    self.links = {} # UniLink -> LinkData
    self.ports = {} # (dpid,port) -> LinkData
    self.switches = {} # dpid -> port -> LinkData
    self.tree_links = set()

  def clear_tree (self):
    pass

  def add_to_tree (self, l):
    pass

  def get_link (self, link):
    pass

  def _add_port (self, sw, port, link):
    pass

  def get_port (self, port): # port is (dpid, port)
    pass

  def iterlinks (self, sw=None):
    """
    Iterate links, optionally only those on a given switch
    """
    pass



class SpanningForest (object):
  def __init__ (self, mode=None):
    if mode is None: mode = 'stable'
    self._mode_function = getattr(type(self), '_compute_' + mode)
    self.log = log
    self.topo = Topo()
    self.switches = {} # dpid -> Switch
    self.t = None
    core.listen_to_dependencies(self)

  def _all_dependencies_met (self):
    pass

  def _handle_timer (self):
    pass

  def _handle_openflow_PortStatus (self, e):
    # Should have the switch...
    pass

  def _handle_openflow_discovery_LinkEvent (self, e):
    pass

  def _handle_openflow_ConnectionUp (self, event):
    pass

  def _handle_openflow_ConnectionDown (self, event):
    pass

  def _compute (self):
    pass

  def _compute_nx (self):
    """
    Computes a spanning tree using NetworkX
    """
    pass

  def _compute_stable (self):
    pass

  def _compute_unstable (self):
    pass

  def _compute_randomized (self):
    pass

  def _compute_simple (self, stable=True, randomize=False):
    """
    Computes a spanning tree aiming for stability

    If stable=True, we prioritize reusing the same links we used the last
    time we ran so that a minimal number of changes should be made.

    It's not particularly efficient, but should be fine for reasonably
    sized graphs.
    """
    pass



def launch (mode=None):
  pass
