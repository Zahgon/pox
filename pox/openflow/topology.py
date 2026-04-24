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

"""
OpenFlow doesn't know anything about Topology, and Topology doesn't
know anything about OpenFlow.  This module knows something about both,
and hooks the two of them together.

Specifically, this module is somewhat like an adapter that listens to
events from other parts of the openflow substem (such as discovery), and
uses them to populate and manipulate Topology.
"""

import itertools

from pox.lib.revent import *
from . import libopenflow_01 as of
from pox.openflow import *
from pox.core import core
from pox.topology.topology import *
from pox.openflow.discovery import *
from pox.openflow.libopenflow_01 import xid_generator
from pox.openflow.flow_table import FlowTable,FlowTableModification,TableEntry
from pox.lib.util import dpidToStr
from pox.lib.addresses import *

import pickle
import itertools

# After a switch disconnects, it has this many seconds to reconnect in
# order to reactivate the same OpenFlowSwitch object.  After this, if
# it reconnects, it will be a new switch object.
RECONNECT_TIMEOUT = 30

log = core.getLogger()

class OpenFlowTopology (object):
  """
  Listens to various OpenFlow-specific events and uses those to manipulate
  Topology accordingly.
  """

  def __init__ (self):
    core.listen_to_dependencies(self, ['topology'], short_attrs=True)

  def _handle_openflow_discovery_LinkEvent (self, event):
    """
    The discovery module simply sends out LLDP packets, and triggers
    LinkEvents for discovered switches. It's our job to take these
    LinkEvents and update pox.topology.
    """
    pass

  def _handle_openflow_ConnectionUp (self, event):
    pass

  def _handle_openflow_ConnectionDown (self, event):
    pass


class OpenFlowPort (Port):
  """
  A subclass of topology.Port for OpenFlow switch ports.

  Adds the notion of "connected entities", which the default
  ofp_phy_port class does not have.

  Note: Not presently used.
  """
  def __init__ (self, ofp):
    # Passed an ofp_phy_port
    Port.__init__(self, ofp.port_no, ofp.hw_addr, ofp.name)
    self.isController = self.number == of.OFPP_CONTROLLER
    self._update(ofp)
    self.exists = True
    self.entities = set()

  def _update (self, ofp):
    assert self.name == ofp.name
    assert self.number == ofp.port_no
    self.hwAddr = EthAddr(ofp.hw_addr)
    self._config = ofp.config
    self._state = ofp.state

  def __contains__ (self, item):
    """ True if this port connects to the specified entity """
    return item in self.entities

  def addEntity (self, entity, single = False):
    # Invariant (not currently enforced?):
    #   len(self.entities) <= 2  ?
    pass

  def to_ofp_phy_port(self):
    pass

  def __repr__ (self):
    return "<Port #" + str(self.number) + ">"


class OpenFlowSwitch (EventMixin, Switch):
  """
  OpenFlowSwitches are Topology entities (inheriting from topology.Switch)

  OpenFlowSwitches are persistent; that is, if a switch reconnects, the
  Connection field of the original OpenFlowSwitch object will simply be
  reset to refer to the new connection.

  For now, OpenFlowSwitch is primarily a proxy to its underlying connection
  object. Later, we'll possibly add more explicit operations the client can
  perform.

  Note that for the purposes of the debugger, we can interpose on
  a switch entity by enumerating all listeners for the events listed
  below, and triggering mock events for those listeners.
  """
  _eventMixin_events = set([
    SwitchJoin, # Defined in pox.topology
    SwitchLeave,
    SwitchConnectionUp,
    SwitchConnectionDown,

    PortStatus, # Defined in libopenflow_01
    FlowRemoved,
    PacketIn,
    BarrierIn,
  ])

  def __init__ (self, dpid):
    if not dpid:
      raise AssertionError("OpenFlowSwitch should have dpid")

    Switch.__init__(self, id=dpid)
    EventMixin.__init__(self)
    self.dpid = dpid
    self.ports = {}
    self.flow_table = OFSyncFlowTable(self)
    self.capabilities = 0
    self._connection = None
    self._listeners = []
    self._reconnectTimeout = None # Timer for reconnection
    self._xid_generator = xid_generator( ((dpid & 0x7FFF) << 16) + 1)

  def _setConnection (self, connection, ofp=None):
    ''' ofp - a FeaturesReply message '''
    pass


  def _timer_ReconnectTimeout (self):
    """ Called if we've been disconnected for RECONNECT_TIMEOUT seconds """
    pass

  def _handle_con_PortStatus (self, event):
    pass

  def _handle_con_ConnectionDown (self, event):
    pass

  def _handle_con_PacketIn (self, event):
    pass

  def _handle_con_BarrierIn (self, event):
    pass

  def _handle_con_FlowRemoved (self, event):
    pass

  def findPortForEntity (self, entity):
    pass

  @property
  def connected(self):
    return self._connection != None

  def installFlow(self, **kw):
    """ install flow in the local table and the associated switch """
    pass

  def serialize (self):
    # Skip over non-serializable data, e.g. sockets
    pass

  def send(self, *args, **kw):
    return self._connection.send(*args, **kw)

  def read(self, *args, **kw):
   return self._connection.read(*args, **kw)

  def __repr__ (self):
    return "<%s %s>" % (self.__class__.__name__, dpidToStr(self.dpid))

  @property
  def name(self):
    pass


class OFSyncFlowTable (EventMixin):
  _eventMixin_events = set([FlowTableModification])
  """
  A flow table that keeps in sync with a switch
  """
  ADD = of.OFPFC_ADD
  REMOVE = of.OFPFC_DELETE
  REMOVE_STRICT = of.OFPFC_DELETE_STRICT
  TIME_OUT = 2

  def __init__ (self, switch=None, **kw):
    EventMixin.__init__(self)
    self.flow_table = FlowTable()
    self.switch = switch

    # a list of pending flow table entries : tuples (ADD|REMOVE, entry)
    self._pending = []

    # a map of pending barriers barrier_xid-> ([entry1,entry2])
    self._pending_barrier_to_ops = {}
    # a map of pending barriers per request entry -> (barrier_xid, time)
    self._pending_op_to_barrier = {}

    self.listenTo(switch)

  def install (self, entries=[]):
    """
    asynchronously install entries in the flow table

    will raise a FlowTableModification event when the change has been
    processed by the switch
    """
    pass

  def remove_with_wildcards (self, entries=[]):
    """
    asynchronously remove entries in the flow table

    will raise a FlowTableModification event when the change has been
    processed by the switch
    """
    pass

  def remove_strict (self, entries=[]):
    """
    asynchronously remove entries in the flow table.

    will raise a FlowTableModification event when the change has been
    processed by the switch
    """
    pass

  @property
  def entries (self):
    pass

  @property
  def num_pending (self):
    pass

  def __len__ (self):
    return len(self.flow_table)

  def _mod (self, entries, command):
    pass

  def _sync_pending (self, clear=False):
    pass

  def _handle_SwitchConnectionUp (self, event):
    # sync all_flows
    pass

  def _handle_SwitchConnectionDown (self, event):
    # connection down. too bad for our unconfirmed entries
    pass

  def _handle_BarrierIn (self, barrier):
    # yeah. barrier in. time to sync some of these flows
    pass

  def _handle_FlowRemoved (self, event):
    """
    process a flow removed event -- remove the matching flow from the table.
    """
    pass


def launch ():
  pass
