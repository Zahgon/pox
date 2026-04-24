# Copyright 2011,2012,2013 Colin Scott
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
Implementation of an OpenFlow flow table
"""

from .libopenflow_01 import *
from pox.lib.revent import *

import time
import math

# FlowTable Entries:
#   match - ofp_match (13-tuple)
#   counters - hash from name -> count. May be stale
#   actions - ordered list of ofp_action_*s to apply for matching packets
class TableEntry (object):
  """
  Models a flow table entry, with a match, actions, and options/flags/counters.

  Note: The current time can either be specified explicitely with the optional
        'now' parameter or is taken from time.time()
  """
  def __init__ (self, priority=OFP_DEFAULT_PRIORITY, cookie=0, idle_timeout=0,
                hard_timeout=0, flags=0, match=ofp_match(), actions=[],
                buffer_id=None, now=None):
    """
    Initialize table entry
    """
    if now is None: now = time.time()
    self.created = now
    self.last_touched = self.created
    self.byte_count = 0
    self.packet_count = 0
    self.priority = priority
    self.cookie = cookie
    self.idle_timeout = idle_timeout
    self.hard_timeout = hard_timeout
    self.flags = flags
    self.match = match
    self.actions = actions
    self.buffer_id = buffer_id

  @staticmethod
  def from_flow_mod (flow_mod):
    pass

  def to_flow_mod (self, flags=None, **kw):
    pass

  @property
  def effective_priority (self):
    """
    Exact matches effectively have an "infinite" priority
    """
    pass

  def is_matched_by (self, match, priority=None, strict=False, out_port=None):
    """
    Tests whether a given match object matches this entry

    Used for, e.g., flow_mod updates

    If out_port is any value besides None, the the flow entry must contain an
    output action to the specified port.
    """
    pass

  def touch_packet (self, byte_count, now=None):
    """
    Updates information of this entry based on encountering a packet.

    Updates both the cumulative given byte counts of packets encountered and
    the expiration timer.
    """
    pass

  def is_idle_timed_out (self, now=None):
    pass

  def is_hard_timed_out (self, now=None):
    pass

  def is_expired (self, now=None):
    """
    Tests whether this flow entry is expired due to its idle or hard timeout
    """
    pass

  def __str__ (self):
    return type(self).__name__ + "\n  " + self.show()

  def __repr__ (self):
    return "TableEntry(" + self.show() + ")"

  def show (self):
    pass

  def flow_stats (self, now=None):
    pass

  def to_flow_removed (self, now=None, reason=None):
    #TODO: Rename flow_stats to to_flow_stats and refactor?
    pass


class FlowTableModification (Event):
  def __init__ (self, added=[], removed=[], reason=None):
    self.added = added
    self.removed = removed

    # Reason for modification.
    # Presently, this is only used for removals and is either one of OFPRR_x,
    # or None if it does not correlate to any of the items in the spec.
    self.reason = reason


class FlowTable (EventMixin):
  """
  General model of a flow table.

  Maintains an ordered list of flow entries, and finds matching entries for
  packets and other entries. Supports expiration of flows.
  """
  _eventMixin_events = set([FlowTableModification])

  def __init__ (self):
    EventMixin.__init__(self)

    # Table is a list of TableEntry sorted by descending effective_priority.
    self._table = []

  def _dirty (self):
    """
    Call when table changes
    """
    pass

  @property
  def entries (self):
    pass

  def __len__ (self):
    return len(self._table)

  def add_entry (self, entry):
    assert isinstance(entry, TableEntry)

    #self._table.append(entry)
    #self._table.sort(key=lambda e: e.effective_priority, reverse=True)

    # Use binary search to insert at correct place
    # This is faster even for modest table sizes, and way, way faster
    # as the tables grow larger.
    priority = entry.effective_priority
    table = self._table
    low = 0
    high = len(table)
    while low < high:
        middle = (low + high) // 2
        if priority >= table[middle].effective_priority:
          high = middle
          continue
        low = middle + 1
    table.insert(low, entry)

    self._dirty()

    self.raiseEvent(FlowTableModification(added=[entry]))

  def remove_entry (self, entry, reason=None):
    pass

  def matching_entries (self, match, priority=0, strict=False, out_port=None):
    pass

  def flow_stats (self, match, out_port=None, now=None):
    pass

  def aggregate_stats (self, match, out_port=None):
    pass

  def _remove_specific_entries (self, flows, reason=None):
    #for entry in flows:
    #  self._table.remove(entry)
    #self._table = [entry for entry in self._table if entry not in flows]
    pass

  def remove_expired_entries (self, now=None):
    pass

  def remove_matching_entries (self, match, priority=0, strict=False,
                               out_port=None, reason=None):
    pass

  def entry_for_packet (self, packet, in_port):
    """
    Finds the flow table entry that matches the given packet.

    Returns the highest priority flow table entry that matches the given packet
    on the given in_port, or None if no matching entry is found.
    """
    pass

  def check_for_overlapping_entry (self, in_entry):
    """
    Tests if the input entry overlaps with another entry in this table.

    Returns true if there is an overlap, false otherwise. Since the table is
    sorted, there is only a need to check a certain portion of it.
    """
    pass
