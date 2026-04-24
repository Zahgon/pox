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
A RIP v2 routing daemon for OpenFlow

This component turns OpenFlow switches into RIP v2 routers.  The
switches must support Open vSwitch / Nicira extensions.

You must run this component once for each switch you want to act as
a RIP router, passing it the DPID of the switch.  You also configure
each interface you want active.  Each interface to be involved in
RIP must be given an IP address, and can also be given a prefix size.
Multiple such IPs/prefixes for each interface can be given separated
by commas.  As well as defining the interface IPs (the sources for
RIP announcements), these define static local routes which will be
spread by RIP.

An example config file (for pox.config) might look like:
  [proto.rip.ovs_rip]
  dpid=10
  eth0=192.168.1.1/24
  4=10.1.0.1/16,10.2.0.1/16

This configures RIP for the switch with DPID 10 (you could also use
POX's canonical DPID format, e.g., 00-00-00-00-00-0a).  The port on
the switch with the name "eth0" will be configured to have IP
192.168.1.1, and the subnet 192.168.1.0/24 should be directly
reachable on this port.  Aside from using port names, one can use
port numbers, as is the case with the next line, which configures
port 4 of the switch to have two IPs and two directly reachable
subnets (if you have port names which are just numbers, this may
be problematic).

You may specify static non-local routes as follows:
  [proto.rip.ovs_rip:static]
  dpid=10
  10.3.0.0/16=192.168.1.3,metric:3

This specifies that the 10.3.0.0/16 subnet should be reachable via
192.168.1.3.  In this case, 192.168.1.3 is reachable directly via
eth0 as seen in the previous config section, but this needn't
actually be the case (though it needs to be reachable somehow when
a packet destined for 10.3.0.0/16 actually arrives!).

See the source comments for info on what the various OpenFlow
tables are used for.
"""

#TODO: Factor out the basic L3 router stuff from the RIP-specific stuff so
#      that the former can be reused for other components.

from pox.core import core
from pox.lib.addresses import IPAddr, parse_cidr
import pox.lib.packet.rip as RIP
import pox.lib.packet as pkt
from pox.lib.recoco import Timer, Task
import socket
from .rip_core import *
from pox.proto.arp_helper import send_arp_reply
from pox.proto.arp_table import ARPTable
from pox.lib.util import dpid_to_str
import pox.openflow.nicira as ovs
import pox.openflow.libopenflow_01 as of

log = core.getLogger()


ARP_IDLE_TIMEOUT = 20
ARP_HARD_TIMEOUT = 60 #TODO: Send periodic ARPs from our side


# We use some packet metadata
DST_IP_REGISTER = ovs.NXM_NX_REG2
OUT_PORT_REGISTER = ovs.NXM_NX_REG3


# Cookies for various table entries
PING_COOKIE = 1
ARP_REPLY_COOKIE = 2
ARP_REQUEST_COOKIE = 3
ARP_TABLE_COOKIE = 4
RIP_PACKET_COOKIE = 5
DHCP_COOKIE = 6


# Table numbers
INGRESS_TABLE = 0
RIP_NET_TABLE = 1
RIP_PORT_TABLE = 2
ARP_TABLE = 3


# The INGRESS table sends various things (ARP) to the controller.
# IP packets, it passes along to RIP_NET after copying the dst
# IP address into DST_IP_REGISTER and decrementing the TTL.

# RIP_NET is one part of the "routing table".  For entries that
# have a gateway, it stores the gateway.  After any lookup,
# RIP_NET resubmits to RIP_PORT, but if the route has a gateway,
# it first rewrites the dst IP to be the IP of the gateway.
# This will then get written back again later.

# RIP_PORT is the second part of the "routing table".  In
# RIP_PORT, the dst IP should be directly attached (either
# because the packet is to a directly attached network or
# because RIP_NET rewrote the destination to be the next
# hop gateway, which should be directly attached), so we
# are using that IP to look up the egress port, which is loaded
# into OUT_PORT_REGISTER.  We also set the source MAC address,
# and finally resubmit to ARP.

# ARP looks up the dst IP, and matching entries set the dst
# Ethernet address, rewrite the dst IP back to the stored
# value in DST_IP_REGISTER, and output to OUT_PORT_REGISTER.
# On a table miss, the packet is sent to the controller with
# ARP_TABLE_COOKIE.  The controller will send an ARP.



class Port (object):
  def __init__ (self):
    self.ips = set()
    self.arp_table = ARPTable()

  @property
  def any_ip (self):
    pass



class OVSRIPRouter (RIPRouter):
  def __init__ (self, dpid):
    self.dpid = dpid

    super(OVSRIPRouter,self).__init__()

    self._ports = {} # portno -> Port
    self._port_cache = {}

    self._deferred_sync_table_pending = 0

    # Caches of switch tables
    self._cur = {RIP_NET_TABLE:{}, RIP_PORT_TABLE:{}}

    # For sloppy duplicate-installation prevention
    #TODO: Do this better
    self._prev = None

    self.log = log

    self.log.info("OVS RIP Router on %s", dpid_to_str(self.dpid))

    core.listen_to_dependencies(self)

  def _handle_core_UpEvent (self, e):
    pass

  def _on_send (self):
    #self.log.debug("Sending timed update")
    pass

  def _deferred_sync_table (self):
    pass

  def _add_entry (self, e):
    pass

  def add_static_route (self, prefix, next_hop, metric=1):
    """
    Adds a static route
    """
    pass

  def add_direct_network (self, iface, ip, prefix):
    """
    Adds a directly attached network (and, implicitly, a network interface)

    iface can either be a port number (int) or port name (string)
    ip is the IP address of the interface (on network 'prefix')
    prefix is the network (IPAddr,prefix_size) of the attached network

    You may call this more than once if the interface has multiple directly
    reachable subnets.
    """
    pass

  def _refresh_ports (self):
    """
    Tries to resolve entries in _port_cache
    """
    pass

  @property
  def all_ips (self):
    pass

  def _clear_table (self, tid):
    if not self._conn: return
    self._invalidate()
    fm = ovs.ofp_flow_mod_table_id()
    fm.command = of.OFPFC_DELETE
    fm.table_id = tid
    self._conn.send(fm)

  def _invalidate (self):
    self._prev = None

  def _init_tables (self):
    pass

  def _init_ingress_table (self):
    pass

  def _init_rip_net_table (self):
    # RIP_NET_TABLE default entry (drop)
    fm = ovs.ofp_flow_mod_table_id()
    fm.table_id = RIP_NET_TABLE
    fm.priority = 0
    self._conn.send(fm)

  def _init_rip_port_table (self):
    # RIP_PORT_TABLE default entry (drop)
    fm = ovs.ofp_flow_mod_table_id()
    fm.table_id = RIP_PORT_TABLE
    fm.priority = 0
    self._conn.send(fm)

  def _init_arp_table (self):
    # ARP_TABLE default entry
    pass

  def _handle_openflow_ConnectionUp (self, event):
    pass

  def _handle_openflow_PortStatus (self, event):
    pass

  def _handle_openflow_PacketIn (self, event):
    pass

  def _do_rip (self, event):
    pass

  def _do_arp_table (self, event):
    pass

  def _do_arp_reply (self, event):
    pass

  def _do_arp_request (self, event):
    pass

  def _add_arp_entry (self, ip_or_arp, eth=None):
    """
    Creates an entry in the switch ARP table

    You can either pass an ARP packet or an IP and Ethernet address
    """
    pass

  def _do_ping (self, event):
    pass

  @property
  def _conn (self):
    """
    The switch object
    """
    pass

  def send_updates (self, force):
    pass

  def sync_table (self):
    if not self._conn: return

    self._cur = {RIP_NET_TABLE:{}, RIP_PORT_TABLE:{}}
    cur = self._cur

    for e in self.table.values():
      if e.metric >= INFINITY: continue
      fm = ovs.ofp_flow_mod_table_id()
      fm.xid = 0
      fm.table_id = RIP_NET_TABLE
      fm.priority = e.size + 1  # +1 because 0 reserved for fallback
      fm.match.dl_type = pkt.ethernet.IP_TYPE
      fm.match.nw_dst = (e.ip, e.size)
      if e.dev is not None:
        # This is for a directly attached network.  It'll be looked up in
        # the port table.
        fm.actions.append(ovs.nx_action_resubmit.resubmit_table(RIP_PORT_TABLE))
      else:
        # This is for a remote network.
        # Load the gateway into the dst IP; it will be looked up in the port
        # table to find the right port.  The real dst IP will get reloaded
        # from a register before egress.
        fm.actions.append(of.ofp_action_nw_addr.set_dst(e.next_hop))
        fm.actions.append(ovs.nx_action_resubmit.resubmit_table(RIP_PORT_TABLE))
      cur[RIP_NET_TABLE][(e.ip, e.size)] = fm

    for e in self.table.values():
      if e.metric >= INFINITY: continue
      fm = ovs.ofp_flow_mod_table_id()
      fm.xid = 0
      fm.table_id = RIP_PORT_TABLE
      fm.priority = e.size + 1  # +1 because 0 reserved for fallback
      fm.match.dl_type = pkt.ethernet.IP_TYPE
      fm.match.nw_dst = (e.ip, e.size)
      if e.dev is not None:
        # This is for a directly attached network.  Look up the port.
        # Also, fix the dst IP address.
        port = self._conn.ports.get(e.dev)
        if port is None: continue
        fm.actions.append(ovs.nx_reg_load(dst=OUT_PORT_REGISTER,
                                          value=e.dev))
        fm.actions.append(of.ofp_action_dl_addr.set_src(port.hw_addr))
        fm.actions.append(ovs.nx_action_resubmit.resubmit_table(ARP_TABLE))
      else:
        # If we get to this table and we don't have a direct entry that
        # matches, we have no working route!
        # Should we install something so that we generate an ICMP unreachable
        # or something?
        pass
      cur[RIP_PORT_TABLE][(e.ip, e.size)] = fm

    if self._conn:
      data1 = b''.join(x.pack() for x in self._cur[RIP_PORT_TABLE].values())
      data2 = b''.join(x.pack() for x in self._cur[RIP_NET_TABLE].values())
      data = data1 + data2
      if data == self._prev: return # Nothing changed

      self._clear_table(RIP_NET_TABLE)
      self._clear_table(RIP_PORT_TABLE)
      self._init_rip_net_table()
      self._init_rip_port_table()

      self.log.debug("Syncing %s port and %s net table entries",
                     len(cur[RIP_PORT_TABLE]),
                     len(cur[RIP_NET_TABLE]))
      self._conn.send(data)

      self._prev = data
      #TODO: Handle errors!



class OVSRIPRouters (object):
  routers_by_dpid = {}

  def add (self, router):
    assert router.dpid not in self.routers_by_dpid
    self.routers_by_dpid[router.dpid] = router

  def get (self, dpid):
    return self.routers_by_dpid[dpid]



def static (dpid, __INSTANCE__=None, **kw):
  pass



def launch (dpid, __INSTANCE__=None, **kw):
  pass
