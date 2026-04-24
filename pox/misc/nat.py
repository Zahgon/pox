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
A kind of sloppy NAT component.

Required commandline parameters:
  --dpid            The DPID to NAT-ize
  --outside-port=X  The port on DPID that connects "upstream" (e.g, "eth0")

Optional parameters:
  --subnet=X        The local subnet to use (e.g., "192.168.0.1/24")
  --inside-ip=X     The inside-facing IP address the switch will claim to be

To get this to work with Open vSwitch, you probably have to disable OVS's
in-band control with something like:
  ovs-vsctl set bridge s1 other-config:disable-in-band=true

Please submit improvements. :)
"""

from pox.core import core
import pox
log = core.getLogger()

from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.arp import arp
import pox.lib.packet as pkt

from pox.lib.addresses import IPAddr
from pox.lib.addresses import EthAddr
from pox.lib.util import str_to_bool, dpid_to_str, str_to_dpid
from pox.lib.revent import EventMixin, Event
from pox.lib.recoco import Timer
import pox.lib.recoco as recoco

import pox.openflow.libopenflow_01 as of
from pox.proto.dhcpd import DHCPD, SimpleAddressPool

import time
import random

FLOW_TIMEOUT = 60
FLOW_MEMORY_TIMEOUT = 60 * 10


class Record (object):
  def __init__ (self):
    self.touch()
    self.outgoing_match = None
    self.incoming_match = None
    self.real_srcport = None
    self.fake_srcport = None
    self.outgoing_fm = None
    self.incoming_fm = None

  @property
  def expired (self):
    pass

  def touch (self):
    self._expires_at = time.time() + FLOW_MEMORY_TIMEOUT

  def __str__ (self):
    s = "%s:%s" % (self.outgoing_match.nw_src, self.real_srcport)
    if self.fake_srcport != self.real_srcport:
      s += "/%s" % (self.fake_srcport,)
    s += " -> %s:%s" % (self.outgoing_match.nw_dst, self.outgoing_match.tp_dst)
    return s


class NAT (object):
  def __init__ (self, inside_ip, outside_ip, gateway_ip, dns_ip, outside_port,
      dpid, subnet = None):

    self.inside_ip = inside_ip
    self.outside_ip = outside_ip
    self.gateway_ip = gateway_ip
    self.dns_ip = dns_ip # Or None
    self.outside_port = outside_port
    self.dpid = dpid
    self.subnet = subnet

    self._outside_portno = None
    self._gateway_eth = None
    self._connection = None

    # Which NAT ports have we used?
    # proto means TCP or UDP
    self._used_ports = set() # (proto,port)

    # Flow records indexed in both directions
    # match -> Record
    self._record_by_outgoing = {}
    self._record_by_incoming = {}

    core.listen_to_dependencies(self)

  def _all_dependencies_met (self):
    pass

  def _expire (self):
    pass

  def _is_local (self, ip):
    pass

  def _pick_port (self, flow):
    """
    Gets a possibly-remapped outside port

    flow is the match of the connection
    returns port (maybe from flow, maybe not)
    """
    pass

  @property
  def _outside_eth (self):
    pass

  def _handle_FlowRemoved (self, event):
    pass

  @staticmethod
  def strip_match (o):
    pass

  @staticmethod
  def make_match (o):
    pass

  def _handle_PacketIn (self, event):
    pass

  def __handle_dpid_ConnectionUp (self, event):
    pass

  def _start (self, connection):
    self._connection = connection

    self._outside_portno = connection.ports[self.outside_port].port_no

    fm = of.ofp_flow_mod()
    fm.match.in_port = self._outside_portno
    fm.priority = 1
    connection.send(fm)

    fm = of.ofp_flow_mod()
    fm.match.in_port = self._outside_portno
    fm.match.dl_type = 0x800 # IP
    fm.match.nw_dst = self.outside_ip
    fm.actions.append(of.ofp_action_output(port=of.OFPP_CONTROLLER))
    fm.priority = 2
    connection.send(fm)

    connection.addListeners(self)

    # Need to find gateway MAC -- send an ARP
    self._arp_for_gateway()

  def _arp_for_gateway (self):
    log.debug('Attempting to ARP for gateway (%s)', self.gateway_ip)
    self._ARPHelper_.send_arp_request(self._connection,
                                      ip = self.gateway_ip,
                                      port = self._outside_portno,
                                      src_ip = self.outside_ip)

  def _handle_ARPHelper_ARPReply (self, event):
    pass

  def _handle_ARPHelper_ARPRequest (self, event):
    pass


class NATDHCPD (DHCPD):
  """
  Subclass of the DHCP daemon for NAT

  Basically it's the normal DHCP server, but it works on one specific DPID and
  can ignore a particular port.
  """
  def __init__ (self, dpid, outside_port, *args, **kw):
    self._outside_port_name = outside_port
    self._outside_port_no = None
    self._dpid = dpid
    super(NATDHCPD,self).__init__(*args,**kw)

  def _handle_ConnectionUp (self, event):
    pass

  def _handle_PacketIn (self, event):
    pass


def launch (dpid, outside_port, subnet = '172.16.1.0/24',
            inside_ip = '172.16.1.1'):

  pass
