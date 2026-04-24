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
A quick-and-dirty learning switch for Open vSwitch

This learning switch requires Nicira extensions as found in Open vSwitch.
Furthermore, you must enable packet-in conversion.  Run with something like:
  ./pox.py openflow.nicira --convert-packet-in forwarding.l2_nx

This forwards based on ethernet source and destination addresses.  Where
l2_pairs installs rules for each pair of source and destination address,
this component uses two tables on the switch -- one for source addresses
and one for destination addresses.  Specifically, we use tables 0 and 1
on the switch to implement the following logic:
0. Is this source address known?
   NO: Send to controller (so we can learn it)
1. Is this destination address known?
   YES:  Forward out correct port
   NO: Flood

Note that unlike the other learning switches *we keep no state in the
controller*.  In truth, we could implement this whole thing using OVS's
learn action, but doing it something like is done here will still allow
us to implement access control or something at the controller.
"""

from pox.core import core
from pox.lib.addresses import EthAddr
import pox.openflow.libopenflow_01 as of
import pox.openflow.nicira as nx
from pox.lib.revent import EventRemove


# Even a simple usage of the logger is much nicer than print!
log = core.getLogger()


def _handle_PacketIn (event):
  pass


def _handle_ConnectionUp (event):
  # Set up this switch.
  # After setting up, we send a barrier and wait for the response
  # before starting to listen to packet_ins for this switch -- before
  # the switch is set up, the packet_ins may not be what we expect,
  # and our responses may not work!

  # Turn on Nicira packet_ins
  pass


def launch ():
  pass
