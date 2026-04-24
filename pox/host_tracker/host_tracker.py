# Copyright 2011 Dorgival Guedes
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
Tracks host location and configuration

Keep track of hosts in the network, where they are and how they are
configured (at least MAC/IP addresses).

For the time being, it keeps tables with the information; later, it should
transfer that information to Topology and handle just the actual
discovery/update of host information.

Timer configuration can be changed when needed (e.g., for debugging) using
the launch facility (check timeoutSec dict and PingCtrl.pingLim).

You can set various timeouts from the commandline.  Names and defaults:
  arpAware=60*2    Quiet ARP-responding entries are pinged after this
  arpSilent=60*20  This is for uiet entries not known to answer ARP
  arpReply=4       Time to wait for an ARP reply before retrial
  timerInterval=5  Seconds between timer routine activations
  entryMove=60     Minimum expected time to move a physical entry

Good values for testing:
  --arpAware=15 --arpSilent=45 --arpReply=1 --entryMove=4

You can also specify how many ARP pings we try before deciding it failed:
  --pingLim=2
"""

from pox.core import core

from pox.lib.addresses import EthAddr
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.arp import arp

from pox.lib.recoco import Timer
from pox.lib.revent import Event, EventHalt

import pox.openflow.libopenflow_01 as of

import pox.openflow.discovery as discovery

from pox.lib.revent.revent import *

import time

import pox
log = core.getLogger()

# Times (in seconds) to use for differente timouts:
timeoutSec = dict(
  arpAware=60*2,   # Quiet ARP-responding entries are pinged after this
  arpSilent=60*20, # This is for uiet entries not known to answer ARP
  arpReply=4,      # Time to wait for an ARP reply before retrial
  timerInterval=5, # Seconds between timer routine activations
  entryMove=60     # Minimum expected time to move a physical entry
  )

# Address to send ARP pings from.
# The particular one here is just an arbitrary locally administered address.
DEFAULT_ARP_PING_SRC_MAC = '02:00:00:00:be:ef'


class HostEvent (Event):
  """
  Event when hosts join, leave, or move within the network
  """
  def __init__ (self, entry, new_dpid = None, new_port = None, join = False,
      leave = False, move = False):
    super(HostEvent,self).__init__()
    self.entry = entry
    self.join = join
    self.leave = leave
    self.move = move

    assert sum(1 for x in [join,leave,move] if x) == 1

    # You can alter these and they'll change where we think it goes...
    self._new_dpid = new_dpid
    self._new_port = new_port

    #TODO: Allow us to cancel add/removes

  @property
  def new_dpid (self):
    """
    New DPID for move events"
    """
    pass

  @property
  def new_port (self):
    """
    New port for move events"
    """
    pass


class Alive (object):
  """
  Holds liveliness information for MAC and IP entries
  """
  def __init__ (self, livelinessInterval=timeoutSec['arpAware']):
    self.lastTimeSeen = time.time()
    self.interval=livelinessInterval

  def expired (self):
    pass

  def refresh (self):
    self.lastTimeSeen = time.time()


class PingCtrl (Alive):
  """
  Holds information for handling ARP pings for hosts
  """
  # Number of ARP ping attemps before deciding it failed
  pingLim=3

  def __init__ (self):
    super(PingCtrl,self).__init__(timeoutSec['arpReply'])
    self.pending = 0

  def sent (self):
    pass

  def failed (self):
    pass

  def received (self):
    # Clear any pending timeouts related to ARP pings
    pass


class IpEntry (Alive):
  """
  This entry keeps track of IP addresses seen from each MAC entry and will
  be kept in the macEntry object's ipAddrs dictionary. At least for now,
  there is no need to refer to the original macEntry as the code is organized.
  """
  def __init__ (self, hasARP):
    if hasARP:
      super(IpEntry,self).__init__(timeoutSec['arpAware'])
    else:
      super(IpEntry,self).__init__(timeoutSec['arpSilent'])
    self.hasARP = hasARP
    self.pings = PingCtrl()

  def setHasARP (self):
    pass


class MacEntry (Alive):
  """
  Not strictly an ARP entry.
  When it gets moved to Topology, may include other host info, like
  services, and it may replace dpid by a general switch object reference
  We use the port to determine which port to forward traffic out of.
  """
  def __init__ (self, dpid, port, macaddr):
    super(MacEntry,self).__init__()
    self.dpid = dpid
    self.port = port
    self.macaddr = macaddr
    self.ipAddrs = {}

  def __str__(self):
    return ' '.join([str(self.dpid), str(self.port), str(self.macaddr)])

  def __eq__ (self, other):
    if other is None:
      return False
    elif type(other) == tuple:
      return (self.dpid,self.port,self.macaddr)==other

    if self.dpid != other.dpid: return False
    if self.port != other.port: return False
    if self.macaddr != other.macaddr: return False
    if self.dpid != other.dpid: return False
    # What about ipAddrs??
    return True

  def __ne__ (self, other):
    return not self.__eq__(other)


class host_tracker (EventMixin):
  """
  Host tracking component
  """
  _eventMixin_events = set([HostEvent])

  def __init__ (self, ping_src_mac = None, install_flow = True,
      eat_packets = True):

    if ping_src_mac is None:
      ping_src_mac = DEFAULT_ARP_PING_SRC_MAC

    self.ping_src_mac = EthAddr(ping_src_mac)
    self.install_flow = install_flow
    self.eat_packets = eat_packets

    # The following tables should go to Topology later
    self.entryByMAC = {}
    self._t = Timer(timeoutSec['timerInterval'],
                    self._check_timeouts, recurring=True)

    # Listen to openflow with high priority if we want to eat our ARP replies
    listen_args = {}
    if eat_packets:
      listen_args={'openflow':{'priority':0}}
    core.listen_to_dependencies(self, listen_args=listen_args)

  def _all_dependencies_met (self):
    pass

  # The following two functions should go to Topology also
  def getMacEntry (self, macaddr):
    pass

  def sendPing (self, macEntry, ipAddr):
    """
    Builds an ETH/IP any-to-any ARP packet (an "ARP ping")
    """
    pass

  def getSrcIPandARP (self, packet):
    """
    Gets source IPv4 address for packets that have one (IPv4 and ARP)

    Returns (ip_address, has_arp).  If no IP, returns (None, False).
    """
    pass

  def updateIPInfo (self, pckt_srcip, macEntry, hasARP):
    """
    Update given MacEntry

    If there is IP info in the incoming packet, update the macEntry
    accordingly. In the past we assumed a 1:1 mapping between MAC and IP
    addresses, but removed that restriction later to accomodate cases
    like virtual interfaces (1:n) and distributed packet rewriting (n:1)
    """
    pass

  def _handle_openflow_ConnectionUp (self, event):
    pass

  def _handle_openflow_PacketIn (self, event):
    """
    Populate MAC and IP tables based on incoming packets.

    Handles only packets from ports identified as not switch-only.
    If a MAC was not seen before, insert it in the MAC table;
    otherwise, update table and enry.
    If packet has a source IP, update that info for the macEntry (may require
    removing the info from antoher entry previously with that IP address).
    It does not forward any packets, just extract info from them.
    """
    pass

  def _check_timeouts (self):
    """
    Checks for timed out entries
    """
    pass
