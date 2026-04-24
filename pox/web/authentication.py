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
Authentication for the POX webserver.

You should be able to mix the BasicAuthMixin into your own request
handlers; see its docstring.  This isn't particularly tested yet.

However, BasicAuthMixin *is* mixed into the SplitterRequestHandler
at the root of the POX web tree.  It's done in a really simple way,
but it means that you can set auth info for the whole tree if you
want.  It's really very basic -- launch this component with
username=password pairs, like:

  [web.authentication:basic]
  user1=password1
  user2=password2

or on the commandline like:

  web.authentication:basic --user1=password1
"""

from pox.core import core

import base64

log = core.getLogger()



class BasicAuthMixin (object):
  """
  Mixin for adding HTTP Basic authentication

  There are two ways to control the authentication.  The first is to override
  _check_basic_auth().  It should return True for valid users.  The default
  implementation implements the second option: it calls the basic_auth_function
  attribute, which should be a function which takes three arguments (the
  handler, the user, and the password) or two arguments (just the user
  and password) and again returns True for acceptable users.  If it is
  None, authentication is disabled (everyone can access the handler).

  In your handlers (e.g., do_GET()), the first line should be something like:
    if not self._do_auth(): return

  There are two ways to control the authentication realm.  The more powerful
  is by overriding the _get_auth_realm() method, which lets you do whatever
  you want.  Alternatively, you can change the auth_realm attribute to
  whatever you like.  There are two magic values.  If it's None (the
  default), the realm will be the path the split, so that each prefix split
  gets its own realm.  If it's True, the realm will be the name of the
  handler class (with a trailing "Handler" removed, if any).
  """
  #TODO: Add MD5 auth

  # auth_realm = None or realm name
  # basic_auth_function = f(user, password)
  # basic_auth_enabled = False will force it off

  def _check_basic_auth (self, user, password):
    """
    Returns True for valid users
    """
    pass

  @property
  def _is_basic_auth_enabled (self):
    pass

  def _get_auth_realm (self):
    pass

  def _send_basic_auth_header (self):
      pass

  def _do_auth (self):
    pass



def basic (__INSTANCE__=None, **kw):
  """
  Lets you add username/password pairs to root of POX webserver
  """
  pass
