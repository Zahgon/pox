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
Input and output from network interfaces.

This wraps PCap, TunTap, etc., to provide a simple, universal, cooperative
interface to network interfaces.

Currently limited to Linux.
"""

from pox.lib.pxpcap import PCap
from queue import Queue
from pox.lib.revent import Event, EventMixin
from pox.lib.ioworker.io_loop import ReadLoop
from pox.core import core
import struct

from fcntl import ioctl
import socket
from pox.lib.addresses import EthAddr, IPAddr
from pox.lib.addresses import parse_cidr, cidr_to_netmask
import os
import ctypes


IFNAMESIZ = 16
IFREQ_SIZE = 40

# from linux/if_tun.h
TUNSETIFF = 0x400454ca
TUNGETIFF = 0x800454d2
IFF_TUN = 0x0001
IFF_TAP = 0x0002
IFF_NO_PI = 0x1000
IFF_ONE_QUEUE = 0x2000
IFF_VNET_HDR = 0x4000
IFF_TUN_EXCL = 0x8000
IFF_MULTI_QUEUE = 0x0100
IFF_ATTACH_QUEUE = 0x0200
IFF_DETACH_QUEUE = 0x0400
IFF_PERSIST = 0x0800
IFF_NOFILTER = 0x1000

#from linux/if.h (flags)
IFF_UP          = 1<<0
IFF_BROADCAST   = 1<<1
IFF_DEBUG       = 1<<2
IFF_LOOPBACK    = 1<<3
IFF_POINTOPOINT = 1<<4
IFF_NOTRAILERS  = 1<<5
IFF_RUNNING     = 1<<6
IFF_NOARP       = 1<<7
IFF_PROMISC     = 1<<8
IFF_ALLMULTI    = 1<<9
IFF_MASTER      = 1<<10
IFF_SLAVE       = 1<<11
IFF_MULTICAST   = 1<<12
IFF_PORTSEL     = 1<<13
IFF_AUTOMEDIA   = 1<<14
IFF_DYNAMIC     = 1<<15
IFF_LOWER_UP    = 1<<16
IFF_DORMANT     = 1<<17
IFF_ECHO        = 1<<18


# Unless IFF_NO_PI, there's a header on packets:
#  16 bits of flags
#  16 bits (big endian?) protocol number


# from /usr/include/linux/sockios.h
SIOCGIFHWADDR = 0x8927
SIOCGIFMTU = 0x8921
SIOCSIFMTU = 0x8922
SIOCGIFFLAGS = 0x8913
SIOCSIFFLAGS = 0x8914
SIOCSIFHWADDR = 0x8924
SIOCGIFNETMASK = 0x891b
SIOCSIFNETMASK = 0x891c
SIOCGIFADDR = 0x8915
SIOCSIFADDR = 0x8916
SIOCGIFBRDADDR = 0x8919
SIOCSIFBRDADDR = 0x891a
SIOCSIFNAME = 0x8923
SIOCADDRT = 0x890B # rtentry (route.h) for IPv4, in6_rtmsg for IPv6
SIOCDELRT = 0x890C


# from /usr/include/linux/if_arp.h
ARPHRD_ETHER = 1
ARPHRD_IEEE802 = 1
ARPHRD_IEEE1394 = 24
ARPHRD_EUI64 = 27
ARPHRD_LOOPBACK = 772
ARPHRD_IPGRE = 778
ARPHRD_IEE802_TR = 800
ARPHRD_IEE80211 = 801
ARPHRD_IEE80211_PRISM = 802
ARPHRD_IEE80211_RADIOTAP = 803
ARPHRD_IP6GRE = 823


class rtentry (object):
  """
  Wrapper for Linux rtentry

  Only tries to capture IPv4 usage.
  Possibly better done with ctypes.
  """
  # flags
  RTF_UP        =  0x0001 # usable
  RTF_GATEWAY   =  0x0002 # dst is gateway
  RTF_HOST      =  0x0004 # host route
  RTF_REINSTATE =  0x0008 # reinstate after timeout
  RTF_DYNAMIC   =  0x0010 # created dynamically (by redirect)
  RTF_MODIFIED  =  0x0020 # modified dynamically (by redirect)
  RTF_MSS       =  0x0040 # use specific MSS for this route
  RTF_WINDOW    =  0x0080 # use per-route window clamping
  RTF_IRTT      =  0x0100 # use initial RTT
  RTF_REJECT    =  0x0200 # reject route

  # fields
  rt_hash = 0
  rt_dst = IPAddr("0.0.0.0")
  rt_gateway = IPAddr("0.0.0.0")
  rt_genmask = IPAddr("0.0.0.0")
  rt_flags = 0
  rt_refcnt = 0
  rt_use = 0
  rt_ifp = 0 # ptr to struct ifnet
  rt_metric = 0
  rt_dev = None # device name
  rt_mss = 0
  rt_window = 0 # window clamping
  rt_irtt = 0 # initial RTT

  def pack (self):
    if self.rt_dev:
      s = ctypes.c_char_p(self.rt_dev + "\0") # Null terminator necessary?
      dev = ctypes.cast(s, ctypes.c_void_p).value
      self._buf = s # You must use the resulting packed string before changing
                    # rt_dev!
    else:
      dev = 0
    return struct.pack("L16s16s16shhLPhPLLH",
      self.rt_hash,
      sockaddr_in(self.rt_dst).pack(),
      sockaddr_in(self.rt_gateway).pack(),
      sockaddr_in(self.rt_genmask).pack(),
      self.rt_flags,
      self.rt_refcnt,
      self.rt_use,
      self.rt_ifp,
      self.rt_metric,
      dev,
      self.rt_mss,
      self.rt_window,
      self.rt_irtt)


class sockaddr_in (object):
  """
  Wrapper for sockaddr_in
  """
  sin_family = socket.AF_INET
  sin_port = 0
  sin_addr = IPAddr("0.0.0.0")

  def __init__ (self, addr=None, port=None):
    if addr is not None:
      self.sin_addr = IPAddr(addr)
    if port is not None:
      self.sin_port = port

  def pack (self):
    r = struct.pack("hH", self.sin_family, self.sin_port)
    r += self.sin_addr.raw
    r += ("\0" * 8)
    return r


class Interface (object):
  """
  Simple interface to tun/tap driver

  Currently only for Linux.  IIRC, shouldn't be too hard to adapt for BSD.
  Other OSes will probably need a fair amount of work.
  """
  #TODO: Setters

  def __init__ (self, name):
    self._name = name

  def __str__ (self):
    return "%s('%s')" % (type(self).__name__, self.name)

  @property
  def name (self):
    pass

  @name.setter
  def name (self, value):
    pass

  @property
  def ipv6_enabled (self):
    pass

  @ipv6_enabled.setter
  def ipv6_enabled (self, value):
    pass

  @property
  def ip_forwarding (self):
    pass

  @ip_forwarding.setter
  def ip_forwarding (self, value):
    pass

  @property
  def mtu (self):
    pass

  @mtu.setter
  def mtu (self, value):
    pass

  @property
  def flags (self):
    pass

  @flags.setter
  def flags (self, value):
    pass

  def set_flags (self, flags, on=True):
    pass

  def unset_flags (self, flags):
    pass

  @property
  def promiscuous (self):
    pass

  @promiscuous.setter
  def promiscuous (self, value):
    pass

  @property
  def is_up (self):
    pass

  @is_up.setter
  def is_up (self, value):
    pass

  @property
  def is_running (self):
    pass

  @property
  def arp_enabled (self):
    pass

  @arp_enabled.setter
  def arp_enabled (self, value):
    pass

  @property
  def ip_addr (self):
    pass

  @ip_addr.setter
  def ip_addr (self, value):
    pass

  @property
  def netmask (self):
    pass

  @netmask.setter
  def netmask (self, value):
    pass

  @property
  def broadcast_addr (self):
    pass

  @broadcast_addr.setter
  def broadcast_addr (self, value):
    pass

  @property
  def eth_addr (self):
    pass

  @eth_addr.setter
  def eth_addr (self, value):
    pass

  def _ioctl_get_ipv4 (self, which):
    pass

  def _ioctl_set_ipv4 (self, which, value):
    pass

  @staticmethod
  def _get_ipv4 (sa):
    pass

  @staticmethod
  def _get_eth (sa):
    pass

  def add_default_route (self, *args, **kw):
    pass

  def add_route (self, network, gateway=None, dev=(), metric=0):
    """
    Add routing table entry

    If dev is unspecified, it defaults to this device
    """
    pass

  def del_route (self, network, gateway=None, dev=(), metric=0):
    """
    Remove a routing table entry

    If dev is unspecified, it defaults to this device
    """
    pass

  def _add_del_route (self, network, gateway=None, dev=(), metric=0,
                      command=None):
    """
    Add or remove a routing table entry

    If dev is unspecified, it defaults to this device
    """
    pass



class TunTap (object):
  """
  Simple wrapper for tun/tap interfaces

  Looks like a file-like object.  You should be able to read/write it, select
  on it, etc.
  """
  def __init__ (self, name=None, tun=False, raw=False):
    """
    Create tun or tap

    By default, it creates a new tun or tap with a default name.  If you
    specify a name, it will either try to create it (if it doesn't exist),
    or try to use an existing interface (for which you must have permission).
    Defaults to tap (Ethernet) mode.  Specify tun=True for tun (IP) mode.
    Specify raw=True to skip the 32 bits of flag/protocol metadata.
    """
    if name is None: name = ""
    openflags = os.O_RDWR
    try:
      openflow |= os.O_BINARY
    except:
      pass
    self._f = os.open("/dev/net/tun", openflags)

    # an ifreq is IFREQ_SIZE bytes long, starting with an interface name
    # (IFNAMESIZ bytes) followed by a big union.

    self.is_tun = tun
    self.is_tap = not tun
    self.is_raw = raw

    flags = 0

    if tun: flags |= IFF_TUN
    else:   flags |= IFF_TAP

    if raw: flags |= IFF_NO_PI

    ifr = struct.pack(str(IFNAMESIZ) + "sH", name, flags)
    ifr += "\0" * (IFREQ_SIZE - len(ifr))

    ret = ioctl(self.fileno(), TUNSETIFF, ifr)
    self.name = ret[:IFNAMESIZ]
    iflags = flags
    ifr = struct.pack(str(IFNAMESIZ) + "sH", name, 0)
    ifr += "\0" * (IFREQ_SIZE - len(ifr))
    ret = ioctl(self.fileno(), TUNGETIFF, ifr)
    flags = struct.unpack("H", ret[IFNAMESIZ:IFNAMESIZ+2])[0]
    self.is_tun = (flags & IFF_TUN) == IFF_TUN
    self.is_tap = not self.is_tun
    #self.is_raw = (flags & IFF_NO_PI) == IFF_NO_PI

  def fileno (self):
    return self._f

  def write (self, data):
    return os.write(self.fileno(), data)

  def read (self, n):
    return os.read(self.fileno(), n)

  def close (self):
    return os.close(self.fileno())

  @property
  def eth_addr (self):
    pass


class RXData (Event):
  """
  Event fired when an interface receives data
  """
  def __init__ (self, interface, data):
    self.interface = interface
    self.data = data


class PCapInterface (Interface, EventMixin):
  _eventMixin_events = set([
    RXData,
  ])

  def __init__ (self, name):
    Interface.__init__(self, name)
    EventMixin.__init__(self)
    self._q = Queue()
    p = PCap(name, callback=self._pcap_cb, start=False)
    p.set_direction(True, False) # Incoming, not outgoing
    p.start()
    self.pcap = p
    core.add_listener(self._handle_GoingDownEvent)

  def _handle_GoingDownEvent (self, event):
    pass

  def send (self, data):
    if self.pcap is None: return
    self.pcap.inject(data)

  def _pcap_cb (self, obj, data, sec, usec, length):
    """
    Handles incoming data from pcap

    This may not be on the right thread, so we just push it to a thread-safe
    queue and poke the cooperative thread, which will pop it later.
    """
    pass

  def _queue_read (self):
    pass

  def __del__ (self):
    self.close()

  def close (self):
    if self.pcap:
      self.pcap.close()
      self.pcap = None


class TapInterface (Interface, EventMixin):
  _eventMixin_events = set([
    RXData,
  ])

  io_loop = None
  max_read_size = 1600
  default_send_protocol = None

  def __init__ (self, name="", tun=False, raw=False, protocol=None):
    self.tap = None
    self.last_flags = None
    self.last_protocol = None
    if protocol: self.default_send_protocol = protocol
    self.io_loop = ReadLoop.singleton
    Interface.__init__(self, name)
    EventMixin.__init__(self)
    self.tap = TunTap(name, raw=raw, tun=tun)
    if not name: self._name = self.tap.name
    self.io_loop.add(self)

  @property
  def is_tap (self):
    pass

  @property
  def is_tun (self):
    pass

  def send (self, data, flags=0, protocol=None):
    if not self.tap.is_raw:
      if protocol is None: protocol = self.default_send_protocol or 0
      #FIXME: In the "0" case above, should we fall back to using the Etherype
      #       in the packet?
      if flags or protocol:
        flags = struct.pack("!HH", flags, protocol) # Flags reversed?
      else:
        flags = "\0\0\0\0"
      data = flags + data
    self.tap.write(data)

  def _do_rx (self):
    pass

  def fileno (self):
    # Support fileno so that this can be used in IO loop directly
    return self.tap.fileno()

  def close (self):
    if self.tap:
      self.tap.close()
      self.tap = None
      self.io_loop.remove(self)

  def __del__ (self):
    self.close()
