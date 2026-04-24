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

See host_tracker.host_tracker for more info.
"""

from pox.core import core
from . import host_tracker
log = core.getLogger()
import logging
log.setLevel(logging.INFO)
from pox.lib.addresses import EthAddr

def launch (src_mac = None, no_flow = False, **kw):
  pass
