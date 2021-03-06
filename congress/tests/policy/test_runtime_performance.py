# Copyright (c) 2015 VMware, Inc. All rights reserved.
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
#
from congress.openstack.common import log as logging
from congress.policy import base
from congress.policy.compile import Literal
from congress.policy import runtime
from congress.tests import base as testbase
from congress.tests import helper

LOG = logging.getLogger(__name__)

NREC_THEORY = 'non-recursive theory'
DB_THEORY = 'database'


class TestRuntimePerformance(testbase.TestCase):
    """Tests for Runtime performance that are not specific to any theory.

    To run one test:
      nosetests -v  \
      congress/tests/policy/test_runtime_performance.py:TestRuntimePerformance.test_foo

    To collect profiling data:
      python -m cProfile -o profile.out `which nosetests` -v \
      congress/tests/policy/test_runtime_performance.py:TestRuntimePerformance.test_foo

    To parse and sort profiling data in different ways:
      import pstats
      pstats.Stats('profile.out').strip_dirs().sort_stats("cum").print_stats()
      pstats.Stats('profile.out').strip_dirs().sort_stats("time").print_stats()
      pstats.Stats('profile.out').strip_dirs().sort_stats("calls").print_stats()

    """

    def setUp(self):
        super(TestRuntimePerformance, self).setUp()

        self._runtime = runtime.Runtime()
        self._runtime.create_policy(NREC_THEORY,
                                    kind=base.NONRECURSIVE_POLICY_TYPE)
        self._runtime.create_policy(DB_THEORY, kind=base.DATABASE_POLICY_TYPE)
        self._runtime.debug_mode()
        self._runtime.insert('', target=NREC_THEORY)

    def _create_event(self, table, tuple_, insert, target):
        return runtime.Event(Literal.create_from_table_tuple(table, tuple_),
                             insert=insert, target=target)

    def test_insert_nonrecursive(self):
        MAX = 100
        th = NREC_THEORY
        for i in range(MAX):
            self._runtime.insert('r(%d)' % i, th)

    def test_insert_database(self):
        MAX = 100
        th = DB_THEORY
        for i in range(MAX):
            self._runtime.insert('r(%d)' % i, th)

    def test_update_nonrecursive(self):
        MAX = 10000
        th = NREC_THEORY
        updates = [self._create_event('r', (i,), True, th)
                   for i in range(MAX)]
        self._runtime.update(updates)

    def test_update_database(self):
        MAX = 1000
        th = DB_THEORY
        updates = [self._create_event('r', (i,), True, th)
                   for i in range(MAX)]
        self._runtime.update(updates)

    def test_indexing(self):
        MAX = 100
        th = NREC_THEORY

        for table in ('a', 'b', 'c'):
            updates = [self._create_event(table, (i,), True, th)
                       for i in range(MAX)]
            self._runtime.update(updates)

        # With indexing, this query should take O(n) time where n is MAX.
        # Without indexing, this query will take O(n^3).
        self._runtime.insert('d(x) :- a(x), b(x), c(x)', th)
        ans = ' '.join(['d(%d)' % i for i in range(MAX)])
        self.assertTrue(helper.datalog_equal(self._runtime.select('d(x)',
                                                                  th), ans))

    def test_select(self):
        # with different types of policies (exercise indexing, large sets,
        # many joins, etc)
        pass

    def test_simulate(self):
        # We're interested in latency here.  We think the cost will be the sum
        # of the simulate call + the cost to do and undo the evaluation, so
        # this test should focus on the cost specific to the simulate call, so
        # the the test should do a minimal amount of evaluation.
        pass

    def test_runtime_initialize_tables(self):
        MAX = 1000
        formulas = [('p', 1, 2, 'foo', 'bar', i) for i in range(MAX)]

        th = NREC_THEORY
        self._runtime.initialize_tables(['p'], formulas, th)
