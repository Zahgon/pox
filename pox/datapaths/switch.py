# Copyright 2012,2013 Colin Scott
# Copyright 2012,2013 James McCauley
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
A software OpenFlow switch
"""

"""
TODO
----
* Don't reply to HELLOs -- just send one on connect
* Pass raw OFP packet to rx handlers as well as parsed
* Once previous is done, use raw OFP for error data when appropriate
* Check self.features to see if various features/actions are enabled,
  and act appropriately if they're not (rather than just doing them).
* Virtual ports currently have no config/state, but probably should.
* Provide a way to rebuild, e.g., the action handler table when the
  features object is adjusted.
"""


from pox.lib.util import assert_type, initHelper, dpid_to_str
from pox.lib.revent import Event, EventMixin
from pox.lib.recoco import Timer
from pox.openflow.libopenflow_01 import *
import pox.openflow.libopenflow_01 as of
from pox.openflow.util import make_type_to_unpacker_table
from pox.openflow.flow_table import FlowTable, TableEntry
from pox.lib.packet import *

import logging
import struct
import time


# Multicast address used for STP 802.1D
_STP_MAC = EthAddr('01:80:c2:00:00:00')


class DpPacketOut (Event):
  """
  Event raised when a dataplane packet is sent out a port
  """
  def __init__ (self, node, packet, port):
    assert assert_type("packet", packet, ethernet, none_ok=False)
    self.node = node
    self.packet = packet
    self.port = port
    self.switch = node # For backwards compatability


class SoftwareSwitchBase (object):
  def __init__ (self, dpid, name=None, ports=4, miss_send_len=128,
                max_buffers=100, max_entries=0x7fFFffFF, features=None):
    """
    Initialize switch
     - ports is a list of ofp_phy_ports or a number of ports
     - miss_send_len is number of bytes to send to controller on table miss
     - max_buffers is number of buffered packets to store
     - max_entries is max flows entries per table
    """
    if name is None: name = dpid_to_str(dpid)
    self.name = name

    self.dpid = dpid

    if isinstance(ports, int):
      ports = [self.generate_port(i) for i in range(1, ports+1)]

    self.max_buffers = max_buffers
    self.max_entries = max_entries
    self.miss_send_len = miss_send_len
    self.config_flags = 0
    self._has_sent_hello = False

    self.table = FlowTable()
    self.table.addListeners(self)

    self._lookup_count = 0
    self._matched_count = 0

    self.log = logging.getLogger(self.name)
    self._connection = None

    # buffer for packets during packet_in
    self._packet_buffer = []

    # Map port_no -> openflow.pylibopenflow_01.ofp_phy_ports
    self.ports = {}
    self.port_stats = {}

    for port in ports:
      self.add_port(port)

    if features is not None:
      self.features = features
    else:
      # Set up default features

      self.features = SwitchFeatures()
      self.features.cap_flow_stats = True
      self.features.cap_table_stats = True
      self.features.cap_port_stats = True
      #self.features.cap_stp = True
      #self.features.cap_ip_reasm = True
      #self.features.cap_queue_stats = True
      #self.features.cap_arp_match_ip = True

      self.features.act_output = True
      self.features.act_enqueue = True
      self.features.act_strip_vlan = True
      self.features.act_set_vlan_vid = True
      self.features.act_set_vlan_pcp = True
      self.features.act_set_dl_dst = True
      self.features.act_set_dl_src = True
      self.features.act_set_nw_dst = True
      self.features.act_set_nw_src = True
      self.features.act_set_nw_tos = True
      self.features.act_set_tp_dst = True
      self.features.act_set_tp_src = True
      #self.features.act_vendor = True

    # Set up handlers for incoming OpenFlow messages
    # That is, self.ofp_handlers[OFPT_FOO] = self._rx_foo
    self.ofp_handlers = {}
    for value,name in ofp_type_map.items():
      name = name.split("OFPT_",1)[-1].lower()
      h = getattr(self, "_rx_" + name, None)
      if not h: continue
      assert of._message_type_to_class[value]._from_controller, name
      self.ofp_handlers[value] = h

    # Set up handlers for actions
    # That is, self.action_handlers[OFPAT_FOO] = self._action_foo
    #TODO: Refactor this with above
    self.action_handlers = {}
    for value,name in ofp_action_type_map.items():
      name = name.split("OFPAT_",1)[-1].lower()
      h = getattr(self, "_action_" + name, None)
      if not h: continue
      if getattr(self.features, "act_" + name) is False: continue
      self.action_handlers[value] = h

    # Set up handlers for stats handlers
    # That is, self.stats_handlers[OFPST_FOO] = self._stats_foo
    #TODO: Refactor this with above
    self.stats_handlers = {}
    for value,name in ofp_stats_type_map.items():
      name = name.split("OFPST_",1)[-1].lower()
      h = getattr(self, "_stats_" + name, None)
      if not h: continue
      self.stats_handlers[value] = h

    # Set up handlers for flow mod handlers
    # That is, self.flow_mod_handlers[OFPFC_FOO] = self._flow_mod_foo
    #TODO: Refactor this with above
    self.flow_mod_handlers = {}
    for name,value in ofp_flow_mod_command_rev_map.items():
      name = name.split("OFPFC_",1)[-1].lower()
      h = getattr(self, "_flow_mod_" + name, None)
      if not h: continue
      self.flow_mod_handlers[value] = h

  def _gen_port_name (self, port_no):
    return "%s.%s"%(dpid_to_str(self.dpid, True).replace('-','')[:12], port_no)

  def _gen_ethaddr (self, port_no):
    # May cause problems if you have large DPIDs...
    return EthAddr("02%06x%04x" % (self.dpid % 0x00FFff, port_no % 0xffFF))

  def generate_port (self, port_no, name = None, ethaddr = None):
    dpid = self.dpid
    p = ofp_phy_port()
    p.port_no = port_no
    if ethaddr is None:
      p.hw_addr = self._gen_ethaddr(p.port_no)
    else:
      p.hw_addr = EthAddr(ethaddr)
    if name is None:
      p.name = self._gen_port_name(p.port_no)
    else:
      p.name = name
    # Fill in features sort of arbitrarily
    p.config = OFPPC_NO_STP
    p.curr = OFPPF_10MB_HD
    p.advertised = OFPPF_10MB_HD
    p.supported = OFPPF_10MB_HD
    p.peer = OFPPF_10MB_HD
    return p

  @property
  def _time (self):
    """
    Get the current time

    This should be used for, e.g., calculating timeouts.  It currently isn't
    used everywhere it should be.

    Override this to change time behavior.
    """
    pass

  def _handle_FlowTableModification (self, event):
    """
    Handle flow table modification events
    """
    pass

  def rx_message (self, connection, msg):
    """
    Handle an incoming OpenFlow message
    """
    pass

  def set_connection (self, connection):
    """
    Set this switch's connection.
    """
    pass

  def send (self, message, connection = None):
    """
    Send a message to this switch's communication partner
    """
    if connection is None:
      connection = self._connection
    if connection:
      connection.send(message)
    else:
      self.log.debug("Asked to send message %s, but not connected", message)

  def _rx_hello (self, ofp, connection):
    #FIXME: This isn't really how hello is supposed to work -- we're supposed
    #       to send it immediately on connection.  See _send_hello().
    pass

  def _rx_echo_request (self, ofp, connection):
    """
    Handles echo requests
    """
    pass

  def _rx_features_request (self, ofp, connection):
    """
    Handles feature requests
    """
    pass

  def _rx_flow_mod (self, ofp, connection):
    """
    Handles flow mods
    """
    pass

  def _rx_packet_out (self, packet_out, connection):
    """
    Handles packet_outs
    """
    pass

  def _rx_echo_reply (self, ofp, connection):
    pass

  def _rx_barrier_request (self, ofp, connection):
    pass

  def _rx_get_config_request (self, ofp, connection):
    pass

  def _rx_stats_request (self, ofp, connection):
    pass

  def _rx_set_config (self, config, connection):
    pass

  def _rx_port_mod (self, port_mod, connection):
    pass

  def _rx_vendor (self, vendor, connection):
    # We don't support vendor extensions, so send an OFP_ERROR, per
    # page 42 of spec
    pass

  def _rx_queue_get_config_request (self, ofp, connection):
    """
    Handles an OFPT_QUEUE_GET_CONFIG_REQUEST message.
    """
    pass

  def send_hello (self, force = False):
    """
    Send hello (once)
    """
    pass

  def send_packet_in (self, in_port, buffer_id=None, packet=b'', reason=None,
                      data_length=None):
    """
    Send PacketIn
    """
    pass

  def send_port_status (self, port, reason):
    """
    Send port status

    port is an ofp_phy_port
    reason is one of OFPPR_xxx
    """
    assert assert_type("port", port, ofp_phy_port, none_ok=False)
    assert reason in ofp_port_reason_rev_map.values()
    msg = ofp_port_status(desc=port, reason=reason)
    self.send(msg)

  def send_error (self, type, code, ofp=None, data=None, connection=None):
    """
    Send an error

    If you pass ofp, it will be used as the source of the error's XID and
    data.
    You can override the data by also specifying data.
    """
    pass

  def rx_packet (self, packet, in_port, packet_data = None):
    """
    process a dataplane packet

    packet: an instance of ethernet
    in_port: the integer port number
    packet_data: packed version of packet if available
    """
    pass

  def delete_port (self, port):
    """
    Removes a port

    Sends a port_status message to the controller

    Returns the removed phy_port
    """
    pass

  def add_port (self, port):
    """
    Adds a port

    Sends a port_status message to the controller
    """
    try:
      port_no = port.port_no
    except:
      port_no = port
      port = self.generate_port(port_no, self.dpid)
    if port_no in self.ports:
      raise RuntimeError("Port %s already exists" % (port_no,))
    self.ports[port_no] = port
    self.port_stats[port.port_no] = ofp_port_stats(port_no=port.port_no)
    self.send_port_status(port, OFPPR_ADD)

  def _set_port_config_bit (self, port, bit, value):
    """
    Set a port config bit

    This is called in response to port_mods.  It is passed the ofp_phy_port,
    the bit/mask, and the value of the bit (i.e., 0 if the flag is to be
    unset, or the same value as bit if it is to be set).

    The return value is a tuple (handled, msg).
    If bit is handled, then handled will be True, else False.
    if msg is a string, it will be used as part of a log message.
    If msg is None, there will be no log message.
    If msg is anything else "truthy", an "enabled" log message is generated.
    If msg is anything else "falsy", a "disabled" log message is generated.
    msg is only used when handled is True.
    """
    pass

  def _output_packet_physical (self, packet, port_no):
    """
    send a packet out a single physical port

    This is called by the more general _output_packet().

    Override this.
    """
    pass

  def _output_packet (self, packet, out_port, in_port, max_len=None):
    """
    send a packet out some port

    This handles virtual ports and does validation.

    packet: instance of ethernet
    out_port, in_port: the integer port number
    max_len: maximum packet payload length to send to controller
    """
    pass

  def _buffer_packet (self, packet, in_port=None):
    """
    Buffer packet and return buffer ID

    If no buffer is available, return None.
    """
    pass

  def _process_actions_for_packet_from_buffer (self, actions, buffer_id,
                                               ofp=None):
    """
    output and release a packet from the buffer

    ofp is the message which triggered this processing, if any (used for error
    generation)
    """
    pass

  def _process_actions_for_packet (self, actions, packet, in_port, ofp=None):
    """
    process the output actions for a packet

    ofp is the message which triggered this processing, if any (used for error
    generation)
    """
    pass

  def _flow_mod_add (self, flow_mod, connection, table):
    """
    Process an OFPFC_ADD flow mod sent to the switch.
    """
    pass

  def _flow_mod_modify (self, flow_mod, connection, table, strict=False):
    """
    Process an OFPFC_MODIFY flow mod sent to the switch.
    """
    pass

  def _flow_mod_modify_strict (self, flow_mod, connection, table):
    """
    Process an OFPFC_MODIFY_STRICT flow mod sent to the switch.
    """
    pass

  def _flow_mod_delete (self, flow_mod, connection, table, strict=False):
    """
    Process an OFPFC_DELETE flow mod sent to the switch.
    """
    pass

  def _flow_mod_delete_strict (self, flow_mod, connection, table):
    """
    Process an OFPFC_DELETE_STRICT flow mod sent to the switch.
    """
    pass

  def _action_output (self, action, packet, in_port):
    pass
  def _action_set_vlan_vid (self, action, packet, in_port):
    pass
  def _action_set_vlan_pcp (self, action, packet, in_port):
    pass
  def _action_strip_vlan (self, action, packet, in_port):
    pass
  def _action_set_dl_src (self, action, packet, in_port):
    pass
  def _action_set_dl_dst (self, action, packet, in_port):
    pass
  def _action_set_nw_src (self, action, packet, in_port):
    pass
  def _action_set_nw_dst (self, action, packet, in_port):
    pass
  def _action_set_nw_tos (self, action, packet, in_port):
    pass
  def _action_set_tp_src (self, action, packet, in_port):
    pass
  def _action_set_tp_dst (self, action, packet, in_port):
    pass
  def _action_enqueue (self, action, packet, in_port):
    pass
#  def _action_push_mpls_tag (self, action, packet, in_port):
#    bottom_of_stack = isinstance(packet.next, mpls)
#    packet.next = mpls(prev = packet.pack())
#    if bottom_of_stack:
#      packet.next.s = 1
#    packet.type = action.ethertype
#    return packet
#  def _action_pop_mpls_tag (self, action, packet, in_port):
#    if not isinstance(packet.next, mpls):
#      return packet
#    if not isinstance(packet.next.next, str):
#      packet.next.next = packet.next.next.pack()
#    if action.ethertype in ethernet.type_parsers:
#      packet.next = ethernet.type_parsers[action.ethertype](packet.next.next)
#    else:
#      packet.next = packet.next.next
#    packet.ethertype = action.ethertype
#    return packet
#  def _action_set_mpls_label (self, action, packet, in_port):
#    if not isinstance(packet.next, mpls):
#      mock = ofp_action_push_mpls()
#      packet = push_mpls_tag(mock, packet)
#    packet.next.label = action.mpls_label
#    return packet
#  def _action_set_mpls_tc (self, action, packet, in_port):
#    if not isinstance(packet.next, mpls):
#      mock = ofp_action_push_mpls()
#      packet = push_mpls_tag(mock, packet)
#    packet.next.tc = action.mpls_tc
#    return packet
#  def _action_set_mpls_ttl (self, action, packet, in_port):
#    if not isinstance(packet.next, mpls):
#      mock = ofp_action_push_mpls()
#      packet = push_mpls_tag(mock, packet)
#    packet.next.ttl = action.mpls_ttl
#    return packet
#  def _action_dec_mpls_ttl (self, action, packet, in_port):
#    if not isinstance(packet.next, mpls):
#      return packet
#    packet.next.ttl = packet.next.ttl - 1
#    return packet


  def _stats_desc (self, ofp, connection):
    pass


  def _stats_flow (self, ofp, connection):
    pass

  def _stats_aggregate (self, ofp, connection):
    pass

  def _stats_table (self, ofp, connection):
    # Some of these may come from the actual table(s) in the future...
    pass

  def _stats_port (self, ofp, connection):
    pass

  def _stats_queue (self, ofp, connection):
    # We don't support queues whatsoever so either send an empty list or send
    # an OFP_ERROR if an actual queue is requested.
    pass


  def __repr__ (self):
    return "%s(dpid=%s, num_ports=%d)" % (type(self).__name__,
                                          dpid_to_str(self.dpid),
                                          len(self.ports))


class SoftwareSwitch (SoftwareSwitchBase, EventMixin):
  _eventMixin_events = set([DpPacketOut])

  def _output_packet_physical (self, packet, port_no):
    """
    send a packet out a single physical port

    This is called by the more general _output_packet().
    """
    pass


class ExpireMixin (object):
  """
  Adds expiration to a switch

  Inherit *before* switch base.
  """
  _expire_period = 2

  def __init__ (self, *args, **kw):
    expire_period = kw.pop('expire_period', self._expire_period)
    super(ExpireMixin,self).__init__(*args, **kw)
    if not expire_period:
      # Disable
      return
    self._expire_timer = Timer(expire_period,
                               self.table.remove_expired_entries,
                               recurring=True)


class OFConnection (object):
  """
  A codec for OpenFlow messages.

  Decodes and encodes OpenFlow messages (ofp_message) into byte arrays.

  Wraps an io_worker that does the actual io work, and calls a
  receiver_callback function when a new message as arrived.
  """

  # Unlike of_01.Connection, this is persistent (at least until we implement
  # a proper recoco Connection Listener loop)
  # Globally unique identifier for the Connection instance
  ID = 0

  # See _error_handler for information the meanings of these
  ERR_BAD_VERSION = 1
  ERR_NO_UNPACKER = 2
  ERR_BAD_LENGTH  = 3
  ERR_EXCEPTION   = 4

  # These methods are called externally by IOWorker
  def msg (self, m):
    self.log.debug("%s %s", str(self), str(m))
  def err (self, m):
    self.log.error("%s %s", str(self), str(m))
  def info (self, m):
    self.log.info("%s %s", str(self), str(m))

  def __init__ (self, io_worker):
    self.starting = True # No data yet
    self.io_worker = io_worker
    self.io_worker.rx_handler = self.read
    self.controller_id = io_worker.socket.getpeername()
    OFConnection.ID += 1
    self.ID = OFConnection.ID
    self.log = logging.getLogger("ControllerConnection(id=%d)" % (self.ID,))
    self.unpackers = make_type_to_unpacker_table()

    self.on_message_received = None

  def set_message_handler (self, handler):
    pass

  def send (self, data):
    """
    Send raw data to the controller.

    Generally, data is a bytes object. If not, we check if it has a pack()
    method and call it (hoping the result will be a bytes object).  This
    way, you can just pass one of the OpenFlow objects from the OpenFlow
    library to it and get the expected result, for example.
    """
    if type(data) is not bytes:
      if hasattr(data, 'pack'):
        data = data.pack()
    self.io_worker.send(data)

  def read (self, io_worker):
    #FIXME: Do we need to pass io_worker here?
    while True:
      message = io_worker.peek()
      if len(message) < 4:
        break

      # Parse head of OpenFlow message by hand
      ofp_version = message[0]
      ofp_type = message[1]

      if ofp_version != OFP_VERSION:
        info = ofp_version
        r = self._error_handler(self.ERR_BAD_VERSION, info)
        if r is False: break
        continue

      message_length = message[2] << 8 | message[3]
      if message_length > len(message):
        break

      if ofp_type >= 0 and ofp_type < len(self.unpackers):
        unpacker = self.unpackers[ofp_type]
      else:
        unpacker = None
      if unpacker is None:
        info = (ofp_type, message_length)
        r = self._error_handler(self.ERR_NO_UNPACKER, info)
        if r is False: break
        io_worker.consume_receive_buf(message_length)
        continue

      new_offset, msg_obj = self.unpackers[ofp_type](message, 0)
      if new_offset != message_length:
        info = (msg_obj, message_length, new_offset)
        r = self._error_handler(self.ERR_BAD_LENGTH, info)
        if r is False: break
        # Assume sender was right and we should skip what it told us to.
        io_worker.consume_receive_buf(message_length)
        continue

      io_worker.consume_receive_buf(message_length)
      self.starting = False

      if self.on_message_received is None:
        raise RuntimeError("on_message_receieved hasn't been set yet!")

      try:
        self.on_message_received(self, msg_obj)
      except Exception as e:
        info = (e, message[:message_length], msg_obj)
        r = self._error_handler(self.ERR_EXCEPTION, info)
        if r is False: break
        continue

    return True

  def _error_handler (self, reason, info):
      """
      Called when read() has an error

      reason is one of OFConnection.ERR_X

      info depends on reason:
      ERR_BAD_VERSION: claimed version number
      ERR_NO_UNPACKER: (claimed message type, claimed length)
      ERR_BAD_LENGTH: (unpacked message, claimed length, unpacked length)
      ERR_EXCEPTION: (exception, raw message, unpacked message)

      Return False to halt processing of subsequent data (makes sense to
      do this if you called connection.close() here, for example).
      """
      if reason == OFConnection.ERR_BAD_VERSION:
        ofp_version = info
        self.log.warn('Unsupported OpenFlow version 0x%02x', info)
        if self.starting:
          message = self.io_worker.peek()
          err = ofp_error(type=OFPET_HELLO_FAILED, code=OFPHFC_INCOMPATIBLE)
          #err = ofp_error(type=OFPET_BAD_REQUEST, code=OFPBRC_BAD_VERSION)
          err.xid = self._extract_message_xid(message)
          err.data = 'Version unsupported'
          self.send(err)
        self.close()
        return False
      elif reason == OFConnection.ERR_NO_UNPACKER:
        ofp_type, message_length = info
        self.log.warn('Unsupported OpenFlow message type 0x%02x', ofp_type)
        message = self.io_worker.peek()
        err = ofp_error(type=OFPET_BAD_REQUEST, code=OFPBRC_BAD_TYPE)
        err.xid = self._extract_message_xid(message)
        err.data = message[:message_length]
        self.send(err)
      elif reason == OFConnection.ERR_BAD_LENGTH:
        msg_obj, message_length, new_offset = info
        t = type(msg_obj).__name__
        self.log.error('Different idea of message length for %s '
                       '(us:%s them:%s)' % (t, new_offset, message_length))
        message = self.io_worker.peek()
        err = ofp_error(type=OFPET_BAD_REQUEST, code=OFPBRC_BAD_LEN)
        err.xid = self._extract_message_xid(message)
        err.data = message[:message_length]
        self.send(err)
      elif reason == OFConnection.ERR_EXCEPTION:
        ex, raw_message, msg_obj = info
        t = type(ex).__name__
        self.log.exception('Exception handling %s' % (t,))
      else:
        self.log.error("Unhandled error")
        self.close()
        return False

  def _extract_message_xid (self, message):
    """
    Extract and return the xid (and length) of an openflow message.
    """
    xid = 0
    if len(message) >= 8:
      #xid = struct.unpack_from('!L', message, 4)[0]
      message_length, xid = struct.unpack_from('!HL', message, 2)
    elif len(message) >= 4:
      message_length = message[2] << 8 | message[3]
    else:
      message_length = len(message)
    return xid

  def close (self):
    self.io_worker.shutdown()

  def get_controller_id (self):
    """
    Return a tuple of the controller's (address, port) we are connected to
    """
    pass

  def __str__ (self):
    return "[Con " + str(self.ID) + "]"


class SwitchFeatures (object):
  """
  Stores switch features

  Keeps settings for switch capabilities and supported actions.
  Automatically has attributes of the form ".act_foo" for all OFPAT_FOO,
  and ".cap_foo" for all OFPC_FOO (as gathered from libopenflow).
  """
  def __init__ (self, **kw):
    self._cap_info = {}
    for val,name in ofp_capabilities_map.items():
      name = name[5:].lower() # strip OFPC_
      name = "cap_" + name
      setattr(self, name, False)
      self._cap_info[name] = val

    self._act_info = {}
    for val,name in ofp_action_type_map.items():
      name = name[6:].lower() # strip OFPAT_
      name = "act_" + name
      setattr(self, name, False)
      self._act_info[name] = val

    self._locked = True

    initHelper(self, kw)

  def __setattr__ (self, attr, value):
    if getattr(self, '_locked', False):
      if not hasattr(self, attr):
        raise AttributeError("No such attribute as '%s'" % (attr,))
    return super(SwitchFeatures,self).__setattr__(attr, value)

  @property
  def capability_bits (self):
    """
    Value used in features reply
    """
    pass

  @property
  def action_bits (self):
    """
    Value used in features reply
    """
    pass

  def __str__ (self):
    l = list(k for k in self._cap_info if getattr(self, k))
    l += list(k for k in self._act_info if getattr(self, k))
    return ",".join(l)
