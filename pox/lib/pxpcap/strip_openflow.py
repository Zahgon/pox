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
A hacky tool to grab packet in/out data from OpenFlow traffic.

Assumes packets are 1:1 with OF messages (as if captured using the
openflow.debug component).

 --infile=<filename>   Input file
 --outfile=<filename>  Output file
 --out-only            Don't include packet_ins
 --in-only             Don't include packet_outs
 --openflow-port=<num> Specify OpenFlow TCP port
"""

#TODO: Clean this up, follow multiple control traffic streams, decode
#      TCP, etc.

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
from pox.lib.util import dpidToStr
import pox.lib.pxpcap.parser as pxparse
import pox.lib.pxpcap.writer as pxwriter

log = core.getLogger()

from pox.lib.pxpcap.writer import PCapRawWriter

_writer = None
_of_port = 6633
_in_only = False
_out_only = False

_pis = 0
_pos = 0

def pi_cb (data, parser):
  pass


def launch (infile, outfile, in_only=False, out_only = False):
  """
  For stripping PI/PO data

  """
  pass
