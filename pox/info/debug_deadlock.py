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
Primitive help for debugging deadlocks.
Prints stack info for all threads.
(Might be more useful if it only printed stack frames that
were not changing, sort of like recoco_spy.)

This was initially factored out from a pox.py modification by
Colin or Andi.
"""

import sys
import time
import inspect
import traceback
import threading
from pox.core import core
import os
base_path = __file__
base_path = os.path.split(base_path)[0]
base_path = os.path.split(base_path)[0]
base_path += os.path.sep

def fmt_tb (tb):
  pass

def _trace_thread_proc ():
  pass


def launch ():

  pass
