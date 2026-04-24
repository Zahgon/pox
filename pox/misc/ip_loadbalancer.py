# Copyright 2013,2014 James McCauley
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
A very sloppy IP load balancer.

Run it with --ip=<Service IP> --servers=IP1,IP2,...

By default, it will do load balancing on the first switch that connects.  If
you want, you can add --dpid=<dpid> to specify a particular switch.

Please submit improvements. :)
"""

from pox.core import core
import pox
log = core.getLogger("iplb")

from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.arp import arp
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.util import str_to_bool, dpid_to_str, str_to_dpid

import pox.openflow.libopenflow_01 as of

import time
import random

FLOW_IDLE_TIMEOUT = 10
FLOW_MEMORY_TIMEOUT = 60 * 5



class MemoryEntry (object):
  """
  Record for flows we are balancing

  Table entries in the switch "remember" flows for a period of time, but
  rather than set their expirations to some long value (potentially leading
  to lots of rules for dead connections), we let them expire from the
  switch relatively quickly and remember them here in the controller for
  longer.

  Another tactic would be to increase the timeouts on the switch and use
  the Nicira extension which can match packets with FIN set to remove them
  when the connection closes.
  """
  def __init__ (self, server, first_packet, client_port):
    self.server = server
    self.first_packet = first_packet
    self.client_port = client_port
    self.refresh()

  def refresh (self):
    self.timeout = time.time() + FLOW_MEMORY_TIMEOUT

  @property
  def is_expired (self):
    pass

  @property
  def key1 (self):
    pass

  @property
  def key2 (self):
    pass


class iplb (object):
  """
  A simple IP load balancer

  Give it a service_ip and a list of server IP addresses.  New TCP flows
  to service_ip will be randomly redirected to one of the servers.

  We probe the servers to see if they're alive by sending them ARPs.
  """
  def __init__ (self, connection, service_ip, servers = []):
    self.service_ip = IPAddr(service_ip)
    self.servers = [IPAddr(a) for a in servers]
    self.con = connection
    self.mac = self.con.eth_addr
    self.live_servers = {} # IP -> MAC,port

    try:
      self.log = log.getChild(dpid_to_str(self.con.dpid))
    except:
      # Be nice to Python 2.6 (ugh)
      self.log = log

    self.outstanding_probes = {} # IP -> expire_time

    # How quickly do we probe?
    self.probe_cycle_time = 5

    # How long do we wait for an ARP reply before we consider a server dead?
    self.arp_timeout = 3

    # We remember where we directed flows so that if they start up again,
    # we can send them to the same server if it's still up.  Alternate
    # approach: hashing.
    self.memory = {} # (srcip,dstip,srcport,dstport) -> MemoryEntry

    self._do_probe() # Kick off the probing

    # As part of a gross hack, we now do this from elsewhere
    #self.con.addListeners(self)

  def _do_expire (self):
    """
    Expire probes and "memorized" flows

    Each of these should only have a limited lifetime.
    """
    t = time.time()

    # Expire probes
    for ip,expire_at in list(self.outstanding_probes.items()):
      if t > expire_at:
        self.outstanding_probes.pop(ip, None)
        if ip in self.live_servers:
          self.log.warn("Server %s down", ip)
          del self.live_servers[ip]

    # Expire old flows
    c = len(self.memory)
    self.memory = {k:v for k,v in self.memory.items()
                   if not v.is_expired}
    if len(self.memory) != c:
      self.log.debug("Expired %i flows", c-len(self.memory))

  def _do_probe (self):
    """
    Send an ARP to a server to see if it's still up
    """
    self._do_expire()

    server = self.servers.pop(0)
    self.servers.append(server)

    r = arp()
    r.hwtype = r.HW_TYPE_ETHERNET
    r.prototype = r.PROTO_TYPE_IP
    r.opcode = r.REQUEST
    r.hwdst = ETHER_BROADCAST
    r.protodst = server
    r.hwsrc = self.mac
    r.protosrc = self.service_ip
    e = ethernet(type=ethernet.ARP_TYPE, src=self.mac,
                 dst=ETHER_BROADCAST)
    e.set_payload(r)
    #self.log.debug("ARPing for %s", server)
    msg = of.ofp_packet_out()
    msg.data = e.pack()
    msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
    msg.in_port = of.OFPP_NONE
    self.con.send(msg)

    self.outstanding_probes[server] = time.time() + self.arp_timeout

    core.callDelayed(self._probe_wait_time, self._do_probe)

  @property
  def _probe_wait_time (self):
    """
    Time to wait between probes
    """
    pass

  def _pick_server (self, key, inport):
    """
    Pick a server for a (hopefully) new connection
    """
    pass

  def _handle_PacketIn (self, event):
    pass


# Remember which DPID we're operating on (first one to connect)
_dpid = None


def launch (ip, servers, dpid = None):
  pass
