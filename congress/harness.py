# Copyright (c) 2014 VMware, Inc. All rights reserved.
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

import ConfigParser
import os
import os.path
import re
import sys

from congress.db import db_policy_rules
from congress.dse import d6cage
from congress import exception
from congress.openstack.common import log as logging
from congress.policy.base import ACTION_POLICY_TYPE


LOG = logging.getLogger(__name__)


def create(rootdir, statedir, config_file, config_override=None):
    """Get Congress up and running when src is installed in rootdir.

    i.e. ROOTDIR=/path/to/congress/congress.
    CONFIG_OVERRIDE is a dictionary of dictionaries with configuration
    values that overrides those provided in CONFIG_FILE.  The top-level
    dictionary has keys for the CONFIG_FILE sections, and the second-level
    dictionaries store values for that section.
    """
    LOG.debug("Starting Congress with rootdir=%s, statedir=%s, "
              "datasource_config=%s, config_override=%s",
              rootdir, statedir, config_file, config_override)

    # create message bus
    cage = d6cage.d6Cage()
    cage.system_service_names.add(cage.name)

    # read in datasource configurations
    cage.config = initialize_config(config_file, config_override)

    # path to congress source dir
    src_path = os.path.join(rootdir, "congress")

    # add policy engine
    engine_path = os.path.join(src_path, "policy/dsepolicy.py")
    LOG.info("main::start() engine_path: %s", engine_path)
    cage.loadModule("PolicyEngine", engine_path)
    cage.createservice(
        name="engine",
        moduleName="PolicyEngine",
        description="Policy Engine (DseRuntime instance)",
        args={'d6cage': cage, 'rootdir': src_path})
    engine = cage.service_object('engine')
    if statedir is not None:
        engine.load_dir(statedir)
    engine.initialize_table_subscriptions()
    cage.system_service_names.add(engine.name)
    engine.debug_mode()  # should take this out for production

    # add policy api
    api_path = os.path.join(src_path, "api/policy_model.py")
    LOG.info("main::start() api_path: %s", api_path)
    cage.loadModule("API-policy", api_path)
    cage.createservice(
        name="api-policy",
        moduleName="API-policy",
        description="API-policy DSE instance",
        args={'policy_engine': engine})
    cage.system_service_names.add('api-policy')

    # add rule api
    api_path = os.path.join(src_path, "api/rule_model.py")
    LOG.info("main::start() api_path: %s", api_path)
    cage.loadModule("API-rule", api_path)
    cage.createservice(
        name="api-rule",
        moduleName="API-rule",
        description="API-rule DSE instance",
        args={'policy_engine': engine})
    cage.system_service_names.add('api-rule')

    # add table api
    api_path = os.path.join(src_path, "api/table_model.py")
    LOG.info("main::start() api_path: %s", api_path)
    cage.loadModule("API-table", api_path)
    cage.createservice(
        name="api-table",
        moduleName="API-table",
        description="API-table DSE instance",
        args={'policy_engine': engine})
    cage.system_service_names.add('api-table')

    # add row api
    api_path = os.path.join(src_path, "api/row_model.py")
    LOG.info("main::start() api_path: %s", api_path)
    cage.loadModule("API-row", api_path)
    cage.createservice(
        name="api-row",
        moduleName="API-row",
        description="API-row DSE instance",
        args={'policy_engine': engine})
    cage.system_service_names.add('api-row')

    # add datasource api
    api_path = os.path.join(src_path, "api/datasource_model.py")
    LOG.info("main::start() api_path: %s", api_path)
    cage.loadModule("API-datasource", api_path)
    cage.createservice(
        name="api-datasource",
        moduleName="API-datasource",
        description="API-datasource DSE instance",
        args={'policy_engine': engine})
    cage.system_service_names.add('api-datasource')

    # add status api
    api_path = os.path.join(src_path, "api/status_model.py")
    LOG.info("main::start() api_path: %s", api_path)
    cage.loadModule("API-status", api_path)
    cage.createservice(
        name="api-status",
        moduleName="API-status",
        description="API-status DSE instance",
        args={'policy_engine': engine})
    cage.system_service_names.add('api-status')

    # add schema api
    api_path = os.path.join(src_path, "api/schema_model.py")
    LOG.info("main::start() api_path: %s", api_path)
    cage.loadModule("API-schema", api_path)
    cage.createservice(
        name="api-schema",
        moduleName="API-schema",
        description="API-schema DSE instance",
        args={'policy_engine': engine})
    cage.system_service_names.add('api-schema')

    # Load policies from database
    for policy in db_policy_rules.get_policies():
        engine.create_policy(
            policy.name, abbr=policy.abbreviation, kind=policy.kind)

    # if this is the first time we are running Congress, need
    #   to create the default theories
    api_policy = cage.service_object('api-policy')

    engine.DEFAULT_THEORY = 'classification'
    engine.builtin_policy_names.add(engine.DEFAULT_THEORY)
    try:
        api_policy.add_item({'name': engine.DEFAULT_THEORY,
                             'description': 'default policy'}, {})
    except KeyError:
        pass

    engine.ACTION_THEORY = 'action'
    engine.builtin_policy_names.add(engine.ACTION_THEORY)
    try:
        api_policy.add_item({'kind': ACTION_POLICY_TYPE,
                             'name': engine.ACTION_THEORY,
                             'description': 'default action policy'},
                            {})
    except KeyError:
        pass

    # have policy-engine subscribe to api calls
    # TODO(thinrichs): either have API publish everything to DSE bus and
    #   have policy engine subscribe to all those messages
    #   OR have API interact with individual components directly
    #   and change all tests so that the policy engine does not need to be
    #   subscribed to 'policy-update'
    engine.subscribe('api-rule', 'policy-update',
                     callback=engine.receive_policy_update)

    # spin up all the configured services, if we have configured them
    if cage.config:
        for name in cage.config:
            if 'module' in cage.config[name]:
                engine.create_policy(name)
                load_data_service(name, cage.config[name], cage, src_path)
                # inform policy engine about schema
                service = cage.service_object(name)
                engine.set_schema(name, service.get_schema())

        # populate rule api data, needs to be done after models are loaded.
        # FIXME(arosen): refactor how we're loading data and api.
        rules = db_policy_rules.get_policy_rules()
        for rule in rules:
            parsed_rule = engine.parse1(rule.rule)
            cage.services['api-rule']['object'].change_rule(
                parsed_rule,
                {'policy_id': rule.policy_name})

    return cage


def load_data_service(service_name, config, cage, rootdir):
    """Load service.

    Load a service if not already loaded. Also loads its
    module if the module is not already loaded.  Returns None.
    SERVICE_NAME: name of service
    CONFIG: dictionary of configuration values
    CAGE: instance to load service into
    ROOTDIR: dir for start of module paths
    """
    if service_name in cage.services:
        return
    if service_name not in cage.config:
        raise exception.DataSourceConfigException(
            "Service %s used in rule but not configured; "
            "tables will be empty" % service_name)
    if 'module' not in config:
        raise exception.DataSourceConfigException(
            "Service %s config missing 'module' entry" % service_name)
    module_path = config['module']
    module_name = re.sub('[^a-zA-Z0-9_]', '_', module_path)
    if not os.path.isabs(module_path) and rootdir is not None:
        module_path = os.path.join(rootdir, module_path)
    if module_name not in sys.modules:
        LOG.info("Trying to create module %s from %s",
                 module_name, module_path)
        cage.loadModule(module_name, module_path)
    LOG.info("Trying to create service %s with module %s",
             service_name, module_name)
    cage.createservice(name=service_name, moduleName=module_name,
                       args=config)


def initialize_config(config_file, config_override):
    """Turn config_file into a dictionary of dictionaries.

    Also doing insulate rest of code from idiosyncracies of ConfigParser.
    """
    if config_override is None:
        config_override = {}
    if config_file is None:
        LOG.info("Starting with override configuration: %s", config_override)
        return config_override
    config = ConfigParser.ConfigParser()
    # If we can't process the config file, we should die
    config.readfp(open(config_file))
    d = {}
    # turn the config into a dictionary of dictionaries,
    #  taking the config_override values into account.
    for section in config.sections():
        if section in config_override:
            override = config_override[section]
        else:
            override = {}
        e = {}
        for opt in config.options(section):
            e[opt] = config.get(section, opt)
        # union e and override, with conflicts decided by override
        e = dict(e, **override)
        d[section] = e
    LOG.info("Starting with configuration: %s", d)
    return d
