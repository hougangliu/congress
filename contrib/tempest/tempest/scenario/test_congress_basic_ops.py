# Copyright 2012 OpenStack Foundation
# Copyright 2013 Hewlett-Packard Development Company, L.P.
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
from tempest import config
from tempest import exceptions
from tempest.openstack.common import log as logging
from tempest.scenario import manager_congress
from tempest import test


CONF = config.CONF
LOG = logging.getLogger(__name__)


class TestPolicyBasicOps(manager_congress.ScenarioPolicyBase):

    @classmethod
    def check_preconditions(cls):
        super(TestPolicyBasicOps, cls).check_preconditions()
        if not (CONF.network.tenant_networks_reachable
                or CONF.network.public_network_id):
            msg = ('Either tenant_networks_reachable must be "true", or '
                   'public_network_id must be defined.')
            cls.enabled = False
            raise cls.skipException(msg)

    def setUp(self):
        super(TestPolicyBasicOps, self).setUp()
        self.keypairs = {}
        self.servers = []

    @test.attr(type='smoke')
    @test.services('compute', 'network')
    def test_policy_basic_op(self):
        self._setup_network_and_servers()
        body = {"rule": "port_security_group(id, security_group_name) "
                        ":-neutronv2:ports(id, tenant_id, name, network_id,"
                        "mac_address, admin_state_up, status, device_id, "
                        "device_owner),"
                        "neutronv2:security_group_port_bindings(id, "
                        "security_group_id), neutronv2:security_groups("
                        "security_group_id, tenant_id1, security_group_name,"
                        "description)"}
        results = self.admin_manager.congress_client.create_policy_rule(
            'classification', body)
        rule_id = results['id']
        self.addCleanup(
            self.admin_manager.congress_client.delete_policy_rule,
            'classification', rule_id)

        # Find the ports of on this server
        ports = self._list_ports(device_id=self.servers[0]['id'])

        def check_data():
            results = self.admin_manager.congress_client.list_policy_rows(
                'classification', 'port_security_group')
            for row in results['results']:
                if (row['data'][0] == ports[0]['id'] and
                    row['data'][1] ==
                        self.servers[0]['security_groups'][0]['name']):
                        return True
            else:
                return False

        if not test.call_until_true(func=check_data, duration=20, sleep_for=4):
            raise exceptions.TimeoutException("Data did not converge in time "
                                              "or failure in server")


class TestCongressDataSources(manager_congress.ScenarioPolicyBase):

    @classmethod
    def check_preconditions(cls):
        super(TestCongressDataSources, cls).check_preconditions()
        if not (CONF.network.tenant_networks_reachable
                or CONF.network.public_network_id):
            msg = ('Either tenant_networks_reachable must be "true", or '
                   'public_network_id must be defined.')
            cls.enabled = False
            raise cls.skipException(msg)

    def test_all_loaded_datasources_are_initialized(self):
        datasources = self.admin_manager.congress_client.list_datasources()

        def _check_all_datasources_are_initialized():
            for datasource in datasources['results']:
                results = (
                    self.admin_manager.congress_client.list_datasource_status(
                        datasource['id']))
                for result in results['results']:
                    if 'initialized' in result.keys():
                        if 'True' not in result.values():
                            return False
            return True

        if not test.call_until_true(
            func=_check_all_datasources_are_initialized,
                duration=20, sleep_for=4):
            raise exceptions.TimeoutException("Data did not converge in time "
                                              "or failure in server")

    def test_all_datasources_have_tables(self):
        datasources = self.admin_manager.congress_client.list_datasources()

        def check_data():
            for datasource in datasources['results']:
                results = (
                    self.admin_manager.congress_client.list_datasource_tables(
                        datasource['id']))
                # NOTE(arosen): if there are no results here we return false as
                # there is something wrong with a driver as it doesn't expose
                # any tables.
                if not results['results']:
                    return False
            return True

        if not test.call_until_true(func=check_data, duration=20, sleep_for=4):
            raise exceptions.TimeoutException("Data did not converge in time "
                                              "or failure in server")
