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
This is a messenger service for interacting with OpenFlow.

There are lots of things that aren't implemented.  Please add!

There's now a simple webservice based on this.  If you add
functionality here, you might want to see about adding it to
the webservice too.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.messenger import *
import sys
import traceback
from pox.openflow.of_json import *
from pox.lib.util import dpidToStr,strToDPID


log = core.getLogger()

def _type_str (m):
  pass


def _ofp_entry (event):
  pass


class OFBot (ChannelBot):
  def _init (self, extra):
    self.enable_packet_ins = False
    self.oflisteners = core.openflow.addListeners(self)

  def _destroyed (self):
    pass

  def _handle_ConnectionUp (self, event):
    #self.send(_ofp_entry(event))
    pass

  def _handle_ConnectionDown (self, event):
    pass

  def _handle_BarrierIn (self, event):
    pass

  def _handle_ErrorIn (self, event):
    pass

  def _handle_SwitchDescReceived (self, event):
    pass

  def _handle_FlowStatsReceived (self, event):
    pass

  def _handle_PacketIn (self, event):
    pass


  def _exec_cmd_packet_out (self, event):
    pass

  def _exec_cmd_get_flow_stats (self, event):
    pass

  def _exec_cmd_set_table (self, event):
    pass

  #TODO: You should actually be able to configure packet in messages...
  #      for example, enabling raw data of the whole packet, and
  #      raw of individual parts.
  def _exec_packetins_True (self, event):
    pass

  def _exec_packetins_False (self, event):
    pass

  def _exec_cmd_list_switches (self, event):
    pass


def launch (nexus = "MessengerNexus"):
  pass
