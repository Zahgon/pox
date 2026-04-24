# Copyright 2011-2013 James McCauley
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

# This file is loosely based on the discovery component in NOX.

"""
This module discovers the connectivity between OpenFlow switches by sending
out LLDP packets. To be notified of this information, listen to LinkEvents
on core.openflow_discovery.

It's possible that some of this should be abstracted out into a generic
Discovery module, or a Discovery superclass.
"""

from pox.lib.revent import *
from pox.lib.recoco import Timer
from pox.lib.util import dpid_to_str, str_to_bool
from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt

import struct
import time
from collections import namedtuple
from random import shuffle, random


log = core.getLogger()


class LLDPSender (object):
  """
  Sends out discovery packets
  """

  SendItem = namedtuple("LLDPSenderItem", ('dpid','port_num','packet'))

  #NOTE: This class keeps the packets to send in a flat list, which makes
  #      adding/removing them on switch join/leave or (especially) port
  #      status changes relatively expensive. Could easily be improved.

  # Maximum times to run the timer per second
  _sends_per_sec = 15

  def __init__ (self, send_cycle_time, ttl = 120):
    """
    Initialize an LLDP packet sender

    send_cycle_time is the time (in seconds) that this sender will take to
      send every discovery packet.  Thus, it should be the link timeout
      interval at most.

    ttl is the time (in seconds) for which a receiving LLDP agent should
      consider the rest of the data to be valid.  We don't use this, but
      other LLDP agents might.  Can't be 0 (this means revoke).
    """
    # Packets remaining to be sent in this cycle
    self._this_cycle = []

    # Packets we've already sent in this cycle
    self._next_cycle = []

    # Packets to send in a batch
    self._send_chunk_size = 1

    self._timer = None
    self._ttl = ttl
    self._send_cycle_time = send_cycle_time
    core.listen_to_dependencies(self)

  def _handle_openflow_PortStatus (self, event):
    """
    Track changes to switch ports
    """
    pass

  def _handle_openflow_ConnectionUp (self, event):
    pass

  def _handle_openflow_ConnectionDown (self, event):
    pass

  def del_switch (self, dpid, set_timer = True):
    pass

  def del_port (self, dpid, port_num, set_timer = True):
    if port_num > of.OFPP_MAX: return
    self._this_cycle = [p for p in self._this_cycle
                        if p.dpid != dpid or p.port_num != port_num]
    self._next_cycle = [p for p in self._next_cycle
                        if p.dpid != dpid or p.port_num != port_num]
    if set_timer: self._set_timer()

  def add_port (self, dpid, port_num, port_addr, set_timer = True):
    if port_num > of.OFPP_MAX: return
    self.del_port(dpid, port_num, set_timer = False)
    packet = self.create_packet_out(dpid, port_num, port_addr)
    self._next_cycle.insert(0, LLDPSender.SendItem(dpid, port_num, packet))
    if set_timer: self._set_timer()
    core.openflow.sendToDPID(dpid, packet) # Send one immediately

  def _set_timer (self):
    if self._timer: self._timer.cancel()
    self._timer = None
    num_packets = len(self._this_cycle) + len(self._next_cycle)

    if num_packets == 0: return

    self._send_chunk_size = 1 # One at a time
    interval = self._send_cycle_time / float(num_packets)
    if interval < 1.0 / self._sends_per_sec:
      # Would require too many sends per sec -- send more than one at once
      interval = 1.0 / self._sends_per_sec
      chunk = float(num_packets) / self._send_cycle_time / self._sends_per_sec
      self._send_chunk_size = chunk

    self._timer = Timer(interval,
                        self._timer_handler, recurring=True)

  def _timer_handler (self):
    """
    Called by a timer to actually send packets.

    Picks the first packet off this cycle's list, sends it, and then puts
    it on the next-cycle list.  When this cycle's list is empty, starts
    the next cycle.
    """
    pass

  def create_packet_out (self, dpid, port_num, port_addr):
    """
    Create an ofp_packet_out containing a discovery packet
    """
    eth = self._create_discovery_packet(dpid, port_num, port_addr, self._ttl)
    po = of.ofp_packet_out(action = of.ofp_action_output(port=port_num))
    po.data = eth.pack()
    return po.pack()

  @staticmethod
  def _create_discovery_packet (dpid, port_num, port_addr, ttl):
    """
    Build discovery packet
    """

    chassis_id = pkt.chassis_id(subtype=pkt.chassis_id.SUB_LOCAL)
    chassis_id.id = ('dpid:' + hex(int(dpid))[2:]).encode()
    # Maybe this should be a MAC.  But a MAC of what?  Local port, maybe?

    port_id = pkt.port_id(subtype=pkt.port_id.SUB_PORT, id=str(port_num))

    ttl = pkt.ttl(ttl = ttl)

    sysdesc = pkt.system_description()
    sysdesc.payload = ('dpid:' + hex(int(dpid))[2:]).encode()

    discovery_packet = pkt.lldp()
    discovery_packet.tlvs.append(chassis_id)
    discovery_packet.tlvs.append(port_id)
    discovery_packet.tlvs.append(ttl)
    discovery_packet.tlvs.append(sysdesc)
    discovery_packet.tlvs.append(pkt.end_tlv())

    eth = pkt.ethernet(type=pkt.ethernet.LLDP_TYPE)
    eth.src = port_addr
    eth.dst = pkt.ETHERNET.NDP_MULTICAST
    eth.payload = discovery_packet

    return eth


class LinkEvent (Event):
  """
  Link up/down event
  """
  def __init__ (self, add, link, event = None):
    self.link = link
    self.added = add
    self.removed = not add
    self.event = event # PacketIn which caused this, if any

  def port_for_dpid (self, dpid):
    pass


class Link (namedtuple("LinkBase",("dpid1","port1","dpid2","port2"))):
  @property
  def uni (self):
    """
    Returns a "unidirectional" version of this link

    The unidirectional versions of symmetric keys will be equal
    """
    pass

  @property
  def flipped (self):
    pass

  @property
  def end (self):
    pass

  def __str__ (self):
    return "%s.%s -> %s.%s" % (dpid_to_str(self[0]),self[1],
                               dpid_to_str(self[2]),self[3])

  def __repr__ (self):
    return "Link(dpid1=%s,port1=%s, dpid2=%s,port2=%s)" % (self.dpid1,
        self.port1, self.dpid2, self.port2)


class Discovery (EventMixin):
  """
  Component that attempts to discover network toplogy.

  Sends out specially-crafted LLDP packets, and monitors their arrival.
  """

  _flow_priority = 65000     # Priority of LLDP-catching flow (if any)
  _link_timeout = 10         # How long until we consider a link dead
  _timeout_check_period = 5  # How often to check for timeouts

  _eventMixin_events = set([
    LinkEvent,
  ])

  _core_name = "openflow_discovery" # we want to be core.openflow_discovery

  Link = Link

  def __init__ (self, install_flow = True, explicit_drop = True,
                link_timeout = None, eat_early_packets = False):
    self._eat_early_packets = eat_early_packets
    self._explicit_drop = explicit_drop
    self._install_flow = install_flow
    if link_timeout: self._link_timeout = link_timeout

    self.adjacency = {} # From Link to time.time() stamp
    self._sender = LLDPSender(self.send_cycle_time)

    # Listen with a high priority (mostly so we get PacketIns early)
    core.listen_to_dependencies(self,
        listen_args={'openflow':{'priority':0xffffffff}})

    Timer(self._timeout_check_period, self._expire_links, recurring=True)

  @property
  def send_cycle_time (self):
    pass

  def install_flow (self, con_or_dpid, priority = None):
    if priority is None:
      priority = self._flow_priority
    if isinstance(con_or_dpid, int):
      con = core.openflow.connections.get(con_or_dpid)
      if con is None:
        log.warn("Can't install flow for %s", dpid_to_str(con_or_dpid))
        return False
    else:
      con = con_or_dpid

    match = of.ofp_match(dl_type = pkt.ethernet.LLDP_TYPE,
                          dl_dst = pkt.ETHERNET.NDP_MULTICAST)
    msg = of.ofp_flow_mod()
    msg.priority = priority
    msg.match = match
    msg.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
    con.send(msg)
    return True

  def _handle_openflow_ConnectionUp (self, event):
    pass

  def _handle_openflow_ConnectionDown (self, event):
    # Delete all links on this switch
    pass

  def _expire_links (self):
    """
    Remove apparently dead links
    """
    pass

  def _handle_openflow_PacketIn (self, event):
    """
    Receive and process LLDP packets
    """
    pass

  def _delete_links (self, links):
    pass

  def is_edge_port (self, dpid, port):
    """
    Return True if given port does not connect to another switch
    """
    for link in self.adjacency:
      if link.dpid1 == dpid and link.port1 == port:
        return False
      if link.dpid2 == dpid and link.port2 == port:
        return False
    return True


class DiscoveryGraph (object):
  """
  Keeps (and optionally exports) a NetworkX graph of the topology

  A nice feature of this is that you can have it export the graph to a
  GraphViz dot file, which you can then look at.  It's a bit easier than
  setting up Gephi or POXDesk if all you want is something quick.  I
  then a little bash script to create an image file from the dot.  If
  you use an image viewer which automatically refreshes when the file
  changes (e.g., Gnome Image Viewer), you have a low-budget topology
  graph viewer.  I export the graph by running the POX component:

    openflow.discovery:graph --export=foo.dot

  And here's the script I use to generate the image:

    touch foo.dot foo.dot.prev
    while true; do
      if [[ $(cmp foo.dot foo.dot.prev) ]]; then
        cp foo.dot foo.dot.prev
        dot -Tpng foo.dot -o foo.png
      fi
      sleep 2
    done
  """
  use_names = True
  def __init__ (self, auto_export_file=None, use_names=None,
                auto_export_interval=2.0):
    self.auto_export_file = auto_export_file
    self.auto_export_interval = auto_export_interval
    if use_names is not None: self.use_names = use_names
    self._export_pending = False
    import networkx as NX
    self.g = NX.MultiDiGraph()
    core.listen_to_dependencies(self)

    self._write_dot = None
    if hasattr(NX, 'write_dot'):
      self._write_dot = NX.write_dot
    else:
      try:
        self._write_dot = NX.drawing.nx_pydot.write_dot
      except ImportError:
        self._write_dot = NX.drawing.nx_agraph.write_dot

    self._auto_export_interval()

  def _auto_export_interval (self):
    if self.auto_export_interval:
      core.call_delayed(self.auto_export_interval,
                        self._auto_export_interval)
      self._do_auto_export()

  def _handle_openflow_discovery_LinkEvent (self, event):
    pass

  def _handle_openflow_PortStatus (self, event):
    pass

  def _do_auto_export (self):
    if not self.auto_export_file: return
    if self._export_pending: return
    self._export_pending = True
    def do_export ():
      pass
    core.call_delayed(0.25, do_export)

  def label_nodes (self):
    for n,d in self.g.nodes(data=True):
      c = core.openflow.connections.get(n)
      name = dpid_to_str(n)
      if self.use_names:
        if c and of.OFPP_LOCAL in c.ports:
          name = c.ports[of.OFPP_LOCAL].name
          if name.startswith("ovs"):
            if "_" in name and name[3:].split("_",1)[0].isdigit():
              name = name.split("_", 1)[-1]
      self.g.node[n]['label'] = name

  def export_dot (self, filename):
    if self._write_dot is None:
      log.error("Can't export graph.  NetworkX has no dot writing.")
      log.error("You probably need to install something.")
      return

    self.label_nodes()

    for u,v,k,d in self.g.edges(data=True, keys=True):
      (d1,p1),(d2,p2) = k
      assert d1 == u
      con1 = core.openflow.connections.get(d1)
      con2 = core.openflow.connections.get(d2)
      c = ''
      if d.get('dead') is True: c += 'gray'
      elif not con1: c += "gray"
      elif p1 not in con1.ports: c += "gray" # Shouldn't happen!
      elif con1.ports[p1].config & of.OFPPC_PORT_DOWN: c += "red"
      elif con1.ports[p1].config & of.OFPPC_NO_FWD: c += "brown"
      elif con1.ports[p1].config & of.OFPPC_NO_FLOOD: c += "blue"
      else: c += "green"
      d['color'] = c
      d['taillabel'] = str(p1)
      d['style'] = 'dashed' if d.get('dead') else 'solid'
    #log.debug("Exporting discovery graph to %s", filename)
    self._write_dot(self.g, filename)


def graph (export = None, dpids_only = False, interval = "2.0"):
  """
  Keep (and optionally export) a graph of the topology

  If you pass --export=<filename>, it will periodically save a GraphViz
  dot file containing the graph.  Normally the graph will label switches
  using their names when possible (based on the name of their "local"
  interface).  If you pass --dpids_only, it will just use DPIDs instead.
  """
  pass


def launch (no_flow = False, explicit_drop = True, link_timeout = None,
            eat_early_packets = False):
  pass
