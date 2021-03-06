# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Utilities and helper functions."""

import contextlib
import shutil
import tempfile

from oslo.config import cfg

from congress.openstack.common import log as logging

LOG = logging.getLogger(__name__)

utils_opts = [
    cfg.StrOpt('tempdir',
               help='Explicitly specify the temporary working directory'),
]
CONF = cfg.CONF
CONF.register_opts(utils_opts)


@contextlib.contextmanager
def tempdir(**kwargs):
    argdict = kwargs.copy()
    if 'dir' not in argdict:
        argdict['dir'] = CONF.tempdir
    tmpdir = tempfile.mkdtemp(**argdict)
    try:
        yield tmpdir
    finally:
        try:
            shutil.rmtree(tmpdir)
        except OSError as e:
            LOG.error(_('Could not remove tmpdir: %s'), e)


def value_to_congress(value):
    if isinstance(value, basestring):
        # TODO(ayip): This throws away high unicode data because congress does
        # not have full support for unicode yet.  We'll need to fix this to
        # handle unicode coming from datasources.
        try:
            unicode(value).encode('ascii')
        except UnicodeEncodeError:
            LOG.warning('Ignoring non-ascii characters')
        return unicode(value).encode('ascii', 'ignore')
    # Check for bool before int, because True and False are also ints.
    elif isinstance(value, bool):
        return str(value)
    elif (isinstance(value, int) or
          isinstance(value, long) or
          isinstance(value, float)):
        return value
    return str(value)
