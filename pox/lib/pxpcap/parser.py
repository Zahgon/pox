# Copyright 2012 James McCauley
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
A parser for pcap data files.

It's not great, but does the job for now.
"""

#TODO:
# Swap names for _sec and _time?
# Add usec to the datetime one?

from datetime import datetime
from struct import unpack_from

class PCapParser (object):
  def __init__ (self, callback = None):
    self._buf = b''
    self._proc = self._proc_global_header
    self._prefix = ''
    self.version = None
    self.snaplen = None
    self.lltype = None

    self.callback = callback

  def _packet (self, data):
    pass

  def _unpack (self, format, data, offset = 0):
    return unpack_from(self._prefix + format, data, offset)

  def _proc_global_header (self):
    pass

  def _proc_header (self):
    pass

  @property
  def _sec (self):
    pass

  @property
  def _time (self):
    pass

  def _proc_packet (self):
    pass

  def feed (self, data):
    pass
