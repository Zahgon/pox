# Copyright 2011-2012 James McCauley
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
This component spies on DNS replies, stores the results, and raises events
when things are looked up or when its stored mappings are updated.

Similar to NOX's DNSSpy component, but with more features.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
import pox.lib.packet.dns as pkt_dns

from pox.lib.addresses import IPAddr
from pox.lib.revent import *

log = core.getLogger()


class DNSUpdate (Event):
  def __init__ (self, item):
    Event.__init__()
    self.item = item

class DNSLookup (Event):
  def __init__ (self, rr):
    Event.__init__()

    self.name = rr.name
    self.qtype = rr.qtype

    self.rr = rr
    for t in pkt_dns.rrtype_to_str.values():
      setattr(self, t, False)
    t = pkt_dns.rrtype_to_str.get(rr.qtype)
    if t is not None:
      setattr(self, t, True)
      setattr(self, "OTHER", False)
    else:
      setattr(self, "OTHER", True)


class DNSSpy (EventMixin):
  _eventMixin_events = set([ DNSUpdate, DNSLookup ])

  def __init__ (self, install_flow = True):
    self._install_flow = install_flow

    self.ip_to_name = {}
    self.name_to_ip = {}
    self.cname = {}

    core.openflow.addListeners(self)

    # Add handy function to console
    core.Interactive.variables['lookup'] = self.lookup

  def _handle_ConnectionUp (self, event):
    pass

  def lookup (self, something):
    pass

  def _record (self, ip, name):
    # Handle reverse lookups correctly?
    pass

  def _record_cname (self, name, cname):
    pass

  def _handle_PacketIn (self, event):
    pass


def launch (no_flow = False):
  pass
