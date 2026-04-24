# Copyright 2013,2017 James McCauley
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
DHCP Client stuff
"""

from pox.core import core
log = core.getLogger()

import pox.lib.packet as pkt

from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.util import dpid_to_str, str_to_dpid
from pox.lib.revent import EventMixin, Event
import pox.lib.recoco as recoco

import pox.openflow.libopenflow_01 as of

import time
import random


class DHCPOffer (Event):
  """
  Fired when an offer has been received

  If you want to immediately accept it, do accept().
  If you want to reject it, do reject().
  If you want to defer acceptance, do nothing.
  """
  def __init__ (self, p):
    super(DHCPOffer,self).__init__()

    self.offer = p

    self.address = p.yiaddr
    self.server = p.siaddr
    o = p.options.get(p.SERVER_ID_OPT)
    if o: self.server = o.addr

    o = p.options.get(p.SUBNET_MASK_OPT)
    self.subnet_mask = o.addr if o else None
    o = p.options.get(p.ROUTERS_OPT)
    self.routers = o.addrs if o else []
    o = p.options.get(p.DNS_SERVER_OPT)
    self.dns_servers = o.addrs if o else []
    o = p.options.get(p.REQUEST_LEASE_OPT)
    o = o.seconds if o is not None else 86400 # Hmmm...

    self._accept = None

  def reject (self):
    pass

  def accept (self):
    self._accept = True

  def option (self, option, default=None):
    pass


class DHCPOffers (Event):
  """
  Fired when all offers in time window have been received
  """
  def __init__ (self, offers):
    super(DHCPOffers,self).__init__()
    self.offers = offers
    self.accepted = None

  def accept (self, offer):
    assert offer in self.offers
    self.accepted = offer


class DHCPLeased (Event):
  """
  Fired when a lease has been confirmed
  """
  def __init__ (self, lease):
    super(DHCPLeased,self).__init__()
    # Lease is the appropriate offer.
    self.lease = lease


class DHCPClientError (Event):
  pass


class DHCPClientBase (EventMixin):
  """
  A DHCP client

  Currently doesn't do lots of stuff "right" according the RFC2131 Section 4.4,
  and the state/timeout management is pretty bad.  It does mostly serve to get
  you an address under simple circumstances, though.
  Feel free to add improvements!
  """
  """
  TODO:
  * Renew
  * Keep track of lease times
  """
  """
  Usage (subclasses):
  * Implement _send_data()
  * Call _rx() with packets
  Usage (consumers):
  * Set .state = INIT
  * Handle events
  """

  _eventMixin_events = set([DHCPOffer, DHCPOffers, DHCPLeased,
                            DHCPClientError])

  _xid = random.randint(1000,0xffFFffFF)

  TOTAL_TIMEOUT = 8
  OFFER_TIMEOUT = 2
  REQUEST_TIMEOUT = 2
  DISCOVER_TIMEOUT = 2

  # Client states
  INIT = 'INIT'
  INIT_REBOOT = 'INIT_REBOOT'
  SELECTING = 'SELECTING'
  REBOOTING = 'REBOOTING'
  REQUESTING = 'REQUESTING'
  REBINDING = 'REBINDING'
  BOUND = 'BOUND'
  RENEWING = 'RENEWING'

  # Not real DHCP states
  NEW = '<NEW>'
  ERROR = '<ERROR>'
  IDLE = '<IDLE>'

  # Parameters to request (in discover)
  param_requests = [
    pkt.DHCP.DHCPDNSServersOption,
    pkt.DHCP.DHCPRoutersOption,
    pkt.DHCP.DHCPSubnetMaskOption,
  ]

  #FIXME: install_flows doesn't belong here?
  def __init__ (self,
                port_eth = None,
                auto_accept = False,
                install_flows = True,
                offer_timeout = None,
                request_timeout = None,
                total_timeout = None,
                discovery_timeout = None,
                name = None):

    # Eth addr of port
    self.port_eth = port_eth

    # Accept first offer?
    # If True the first non-rejected offer is used immediately, without
    # waiting for the offer_timeout window to close.
    self.auto_accept = auto_accept

    self.install_flows = install_flows

    if name is None:
      self.log = log
    else:
      self.log = core.getLogger(name)

    self._state = self.NEW
    self._start = None

    # We keep track of all offers we received
    self.offers = []

    # XID that messages should have to us should have
    self.offer_xid = None
    self.ack_xid = None

    ### Accepted offer
    ##self.accepted = None

    # Requested offer
    self.requested = None

    # Bound offer
    self.bound = None

    # How long to wait total
    self.total_timeout = total_timeout or self.TOTAL_TIMEOUT
    self.total_timer = None

    # How long to wait for the first offer following a discover
    # If we don't hear one, we'll resend the discovery
    self.discover_timeout = discovery_timeout or self.DISCOVER_TIMEOUT
    self.discover_timer = None

    # How long to wait for offers after the first one
    self.offer_timeout = offer_timeout or self.OFFER_TIMEOUT
    self.offer_timer = None

    # How long to wait for ACK/NAK on requested offer
    self.request_timeout = request_timeout or self.REQUEST_TIMEOUT
    self.request_timer = None

    # We add and remove the PacketIn listener.  This is its event ID
    self._packet_listener = None

  def _total_timeout (self):
    # If this goes off and we haven't finished, tell the user we failed
    pass

  @property
  def _secs (self):
    pass

  @property
  def state (self):
    pass

  @state.setter
  def state (self, state):
    pass

  def _state_transition (self, old, state):
    pass

  def _do_total_timeout (self):
    pass

  def _add_param_requests (self, msg):
    pass

  def _discover (self):
    pass

  def _request (self):
    pass

  @classmethod
  def _new_xid (cls):
    pass

  def _send (self, msg, msg_type):
    pass

  def _send_dhcp (self, msg):
    pass

  def _send_data (self, data):
    raise RuntimeError("_send_data() unimplemented")

  def _rx (self, parsed):
    """
    Input packet here
    """
    pass

  def _exec_offer (self, p):
    pass

  def _exec_request_ack (self, p):
    pass

  def _exec_request_nak (self, p):
    pass

  def _do_accept (self):
    ev = DHCPOffers(self.offers)
    for o in self.offers:
      if o._accept is True:
        ev.accepted = o
        break
    if ev.accepted is None:
      for o in self.offers:
        if o._accept is not False:
          ev.accepted = o
          break

    self.raiseEventNoErrors(ev)

    #TODO: Properly decline offers

    if ev.accepted is None:
      self.log.info('No offer accepted')
      self.state = self.IDLE
      return

    self.requested = ev.accepted

    self.state = self.REQUESTING


class OFDHCPClient (DHCPClientBase):
  """
  DHCP client via an OpenFlow switch
  """

  """
  TODO:
  * Bind port_name -> port_no later?
  """

  def __init__ (self, dpid, port, **kw):
    """
    Initializes

    port_eth can be True to use the MAC associated with the port by the
      switch, None to use the 'dpid MAC', or an EthAddr.
    """
    self.port_name = port

    if hasattr(dpid, 'dpid'):
      dpid = dpid.dpid
    self.dpid = dpid

    super(OpenFlowDHCPClient,self).__init__(**kw)

    self._try_start()
    if self.state != self.INIT:
      self._listen_for_connection()

  def _handle_PacketIn (self, event):
    pass

  def _send_data (self, data):
    pass

  def _send_of (self, data):
    pass

  def _handle_ConnectionUp (self, event):
    pass

  def _listen_for_connection (self):
    core.openflow.addListenerByName('ConnectionUp', self._handle_ConnectionUp,
                                    once = True)

  def _try_start (self):
    if self.state != self.NEW:
      return

    dpid = self.dpid
    port = self.port_name

    con = core.openflow.connections.get(dpid, None)

    if con is None:
      #raise RuntimeError('DPID %s not connected' % (dpid_to_str(dpid),))
      self._listen_for_connection()
      return

    if isinstance(port, str):
      if port not in con.ports:
        self.log.error('No such port as %s.%s' % (dpid_to_str(dpid), port))
        #raise RuntimeError('No such port as %s.%s' % (dpid_to_str(dpid),port))
        self.state = self.ERROR
        return
      self.portno = con.ports[port].port_no

    if self.port_eth is None:
      self.port_eth = con.eth_addr
    elif self.port_eth is True:
      self.port_eth = con.ports[port].hw_addr

    self.state = self.INIT

  def _state_transition (self, old, state):
    # Make sure we're seeing packets if needed...

    pass


def launch (dpid, port, port_eth = None, name = None, __INSTANCE__ = None):
  """
  Launch

  port_eth unspecified: "DPID MAC"
  port_eth enabled: Port MAC
  port_eth specified: Use that
  """
  pass
