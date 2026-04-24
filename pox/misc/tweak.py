# Copyright 2018 James McCauley
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
Tweak values

This component lets you tweak various values which otherwise you'd need
to write code to do.  For example, lots of classes have default values
stored as class variables, and there isn't always an exposed way to
change them from the commandline or a config file.  With tweak, you
just do:
  misc.tweak=some.thing.Somewhere.value --value=42
"""

import sys
from pox.lib.config_eval import eval_one
from pox.core import core

log = core.getLogger()


def launch (key, value=None, __INSTANCE__=None):
  pass
