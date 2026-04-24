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
A simple hack of info.packet_dump that dumps pcap files to the console.

Use --infile=<filename> to specify the pcap file.
Use --verbose for really verbose dumps.
Use --show to show all packets.
Use --show=<types> to show specific types.
Use --hide=<types> to hide specific types.
Use --max-length=<chars> to limit line lengths.
"""

#TODO: Refactor with packet_dump

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
from pox.lib.util import dpidToStr
import pox.lib.pxpcap.parser as pxparse
import pox.lib.pxpcap.writer as pxwriter

log = core.getLogger()

_verbose = None
_max_length = None
_types = None
_show_by_default = None


def cb (data, parser):
  pass


def launch (infile, verbose = False, max_length = 110,
            hide = False, show = False):
  pass
