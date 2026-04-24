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
Attempts to give help on other components
"""

from __future__ import print_function
import pox.boot as boot
from pox.lib.util import first_of
import inspect
import sys

def _show_args (f,name):
  #TODO: Refactor with pox.boot

  pass


def launch (no_args = False, short = False, **kw):
  """
  Shows help

  Usage: help <args> --component_name
         help <args> --component_name=launcher

  Args are:
    --short    Only summarize docs
    --no-args  Don't show parameter info
  """
  pass
