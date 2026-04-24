# Copyright 2013,2018 James McCauley
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
Software switch with PCap ports

Example:
./pox.py --no-openflow datapaths.pcap_switch --address=localhost

Along with using pcap to connect to real interfaces, there are virtual
ports which can connect to each other.  This is sort of like the OVS
patch panel.  If you have multiple switches running in the same POX
instance, you can use virtual ports to wire them together.

When instantiating a switch from the commandline, port names starting
with a "@" are virtual ports (the "@" is stripped from the eventual
name).  A virtual port is connected to a channel.  If you have multiple
virtual ports connected to the same channel, packets are passed
between them.  If the name you pass in when instantiating the switch
has a *second* "@" in it, the part after the second one is a
channel name.  Thus, you could make two switches connected to each
other with a config file like:

  [datapaths.pcap_switch]
  ports=@eth1@A

  [datapaths.pcap_switch]
  ports=@eth1,@eth2@A

That connects the first switch's eth1 to the second switch's eth2 via
a virtual channel called "A".  And the second switch has a virtual
port called eth1 which isn't connected to anything.
"""

#TODO: Make virtual ports easily reusable by other switch subclasses.

from pox.core import core
from pox.datapaths import do_launch
from pox.datapaths.switch import SoftwareSwitchBase, OFConnection
from pox.datapaths.switch import ExpireMixin
import pox.lib.pxpcap as pxpcap
from queue import Queue
from threading import Thread
import pox.openflow.libopenflow_01 as of
from pox.lib.packet import ethernet
import pox.lib.packet as pkt
import logging
from pox.lib.util import dpid_to_str, str_to_dpid, first_of

log = core.getLogger()

DEFAULT_CTL_PORT = 7791

_switches = {}

def _do_ctl (event):
  pass

def _do_ctl2 (event):
  pass


def launch (address = '127.0.0.1', port = 6633, max_retry_delay = 16,
    dpid = None, ports = '', extra = None, ctl_port = None,
    __INSTANCE__ = None):
  """
  Launches a switch
  """
  pass


class VirtualPort (object):
  """
  A virtual port for the PCapSwitch

  It has the same interface as PCapSwitch
  """
  _patchbay = {} # channel_name -> list of other virtual ports
  debug = True

  def __init__ (self, switch, phy):
    self._channel = None
    self.phy = phy
    self.switch = switch
    self.started = False

  @property
  def hw_addr (self):
    pass

  @property
  def device (self):
    pass

  @property
  def port_no (self):
    pass

  @property
  def channel (self):
    pass

  @channel.setter
  def channel (self, channel):
    pass

  @property
  def is_link_down (self):
    pass

  @is_link_down.setter
  def is_link_down (self, value):
    pass

  def _packet_hook (self, data):
    if not self.debug: return
    if self.channel is not None: return
    # If there's no channel and packet is to this port, log it.
    if isinstance(data, pkt.ethernet):
      if self.hw_addr == data.dst:
        log.info("%s.%s RX: %s", self.switch.name, self.phy.name, data.dump())
      else:
        log.debug("%s.%s RX: %s", self.switch.name, self.phy.name, data.dump())

  def inject (self, data):
    #TODO: Support STP config?  Or does that go in the switch class?
    if self.phy.state & of.OFPPS_LINK_DOWN: return

    self._packet_hook(data)

    if self._channel is None: return

    data = data.pack()

    for p in self._patchbay[self.channel]:
      if p is self: continue
      if not p.started: continue
      if p.phy.state & of.OFPPS_LINK_DOWN: continue
      log.debug("%s.%s -> %s.%s", self.switch.name, self.phy.name,
                                  p.switch.name, p.phy.name)
      p.switch._pcap_rx(p, data, 0, 0, len(data))

  def start (self):
    self.started = True


class PCapSwitch (ExpireMixin, SoftwareSwitchBase):
  # Default level for loggers of this class
  default_log_level = logging.INFO

  # If true, names starting with a "@" are virtual ports
  magic_virtual_port_names = False

  def __init__ (self, **kw):
    """
    Create a switch instance

    Additional options over superclass:
    log_level (default to default_log_level) is level for this instance
    ports is a list of interface names
    """
    log_level = kw.pop('log_level', self.default_log_level)

    self.magic_virtual_port_names = kw.pop("magic_virtual_port_names",
                                           self.magic_virtual_port_names)

    self.q = Queue()
    self.t = Thread(target=self._consumer_threadproc)
    core.addListeners(self)

    ports = kw.pop('ports', [])
    kw['ports'] = []

    super(PCapSwitch,self).__init__(**kw)

    self._next_port = 1

    self.px = {}

    for p in ports:
      self.add_interface(p, start=False)

    self.log.setLevel(log_level)

    for px in self.px.values():
      px.start()

    self.t.start()

  def add_interface (self, name, port_no=-1, on_error=None, start=False,
                     virtual=False):
    """
    Add an interface

    This is usually a PCap interface, unless virtual is set.  If virtual
    is True, this creates a virtual port which isn't connected to any
    channel.  If it's a string, it's the channel name.
    """
    if self.magic_virtual_port_names:
      if name.startswith("@"):
        name = name[1:]
        virtual = True
        if "@" in name:
          name,virtual = name.split("@",1)

    if on_error is None:
      on_error = log.error

    phy = of.ofp_phy_port()
    phy.name = name
    # Fill in features sort of arbitrarily
    phy.curr = of.OFPPF_10MB_HD
    phy.advertised = of.OFPPF_10MB_HD
    phy.supported = of.OFPPF_10MB_HD
    phy.peer = of.OFPPF_10MB_HD

    if virtual:
      px = VirtualPort(self, phy)
      if isinstance(virtual, str):
        px.channel = virtual
    else:
      if not pxpcap.enabled:
        on_error("Not adding port %s because PXPCap is not available", name)
        return
      devs = pxpcap.PCap.get_devices()
      if name not in devs:
        on_error("Device %s not available -- ignoring", name)
        return
      dev = devs[name]
      if dev.get('addrs',{}).get('ethernet',{}).get('addr') is None:
        on_error("Device %s has no ethernet address -- ignoring", name)
        return
      if dev.get('addrs',{}).get('AF_INET') != None:
        on_error("Device %s has an IP address -- ignoring", name)
        return
      for no,p in self.px.items():
        if p.device == name:
          on_error("Device %s already added", name)

      phy.hw_addr = dev['addrs']['ethernet']['addr']

      px = pxpcap.PCap(name, callback = self._pcap_rx, start = False)

    if port_no == -1:
      while True:
        port_no = self._next_port
        self._next_port += 1
        if port_no not in self.ports: break

    if port_no in self.ports:
      on_error("Port %s already exists -- ignoring", port_no)
      return

    phy.port_no = port_no
    self.px[phy.port_no] = px

    if virtual:
      # We create the MAC based on the port_no, so we have to do it here
      # and not earlier.
      phy.hw_addr = self._gen_ethaddr(phy.port_no)

    self.add_port(phy)

    if start:
      px.start()

    return px

  def remove_interface (self, name_or_num):
    pass

  def _handle_GoingDownEvent (self, event):
    pass

  def _consumer_threadproc (self):
    pass

  def rx_batch (self, batch):
    pass

  def _pcap_rx (self, px, data, sec, usec, length):
    if px.port_no is None: return
    self.q.put((px.port_no, data))

  def _output_packet_physical (self, packet, port_no):
    """
    send a packet out a single physical port

    This is called by the more general _output_packet().
    """
    pass
