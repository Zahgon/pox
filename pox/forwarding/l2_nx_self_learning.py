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
This makes Nicira-extension capable switches into learning switches

This uses the "learn" action so that switches become learning switches
*with no controller involvement*.

  ./pox.py openflow.nicira forwarding.l2_nx_self_learning
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.openflow.nicira as nx


log = core.getLogger("l2_nx_self_learning")


def _handle_ConnectionUp (event):
  # Set up this switch.

  # Turn on ability to specify table in flow_mods
  pass



def launch ():
  pass
