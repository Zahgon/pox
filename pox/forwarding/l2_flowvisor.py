# Copyright 2012 James McCauley
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
A modification of l2_pairs to work with FlowVisor on looped topologies.

The spanning_tree component doesn't work with FlowVisor because FlowVisor
does not virtualize the NO_FLOOD bit on switch ports, which is what
the spanning_tree component would need to work properly.

This hack of l2_pairs uses the spanning tree construction from the
spanning_tree component, but instead of using it to modify port bits,
instead of ever actually flooding, it "simulates" flooding by just
adding all of the ports on the spanning tree as individual output
actions.

Requires discovery.
"""

# These next two imports are common POX convention
from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.openflow.spanning_tree as spanning_tree

# Even a simple usage of the logger is much nicer than print!
log = core.getLogger()


# This table maps (switch,MAC-addr) pairs to the port on 'switch' at
# which we last saw a packet *from* 'MAC-addr'.
# (In this case, we use a Connection object for the switch.)
table = {}


# A spanning tree to be used for flooding
tree = {}

def _handle_links (event):
  """
  Handle discovery link events to update the spanning tree
  """
  pass


def _handle_PacketIn (event):
  """
  Handle messages the switch has sent us because it has no
  matching rule.
  """
  pass


def launch ():
  pass
