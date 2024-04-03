#!/usr/bin/python3

import os
import xml.etree.ElementTree as ET

from entrypoint_helpers import env, gen_cfg, str2bool, str2bool_or, exec_app

RUN_USER = env['run_user']
RUN_GROUP = env['run_group']
BAMBOO_INSTALL_DIR = env['bamboo_install_dir']
BAMBOO_HOME = env['bamboo_home']
ATL_DB_TYPE = env.get('atl_db_type')
ATL_BAMBOO_SKIP_CONFIG = str2bool(env.get('atl_bamboo_skip_config'))
ATL_BAMBOO_ENABLE_UNATTENDED_SETUP = str2bool(env.get('atl_bamboo_enable_unattended_setup', 'false'))
ATL_BAMBOO_DISABLE_AGENT_AUTH = str2bool(env.get('atl_bamboo_disable_agent_auth'))
UPDATE_CFG = str2bool_or(env.get('atl_force_cfg_update'), False)

def add_jvm_arg(arg):
    os.environ['JVM_SUPPORT_RECOMMENDED_ARGS'] = os.environ.get('JVM_SUPPORT_RECOMMENDED_ARGS', '') + ' ' + arg

gen_cfg('server.xml.j2', f'{BAMBOO_INSTALL_DIR}/conf/server.xml')
gen_cfg('seraph-config.xml.j2',
        f'{BAMBOO_INSTALL_DIR}/atlassian-bamboo/WEB-INF/classes/seraph-config.xml')
gen_cfg('bamboo-init.properties.j2',
        f'{BAMBOO_INSTALL_DIR}/atlassian-bamboo/WEB-INF/classes/bamboo-init.properties')

if not ATL_BAMBOO_SKIP_CONFIG:
    if 'build_number' not in env:
        it = ET.iterparse('/tmp/pom.xml')
        for _, el in it:
            el.tag = el.tag.split('}', 1)[1]  # strip all namespaces
        pom_xml = it.root
        env['build_number'] = pom_xml.find('.//buildNumber').text
    gen_cfg('bamboo.cfg.xml.j2', f"{BAMBOO_HOME}/bamboo.cfg.xml",
            user=RUN_USER, group=RUN_GROUP, overwrite=UPDATE_CFG)

if ATL_DB_TYPE is not None:
    gen_cfg(f"{ATL_DB_TYPE}.properties.j2",
            f"{BAMBOO_INSTALL_DIR}/atlassian-bamboo/WEB-INF/classes/database-defaults/{ATL_DB_TYPE}.properties")

# Bamboo should not run Repository-stored Specs in Docker while being run in a Docker container itself.
# Only affects the installation phase. Has no effect once Bamboo is set up.
add_jvm_arg('-Dbamboo.setup.rss.in.docker=false')

# Unattended setup pre-seeding file
#
# For full or partial pre-seeding set ATL_BAMBOO_ENABLE_UNATTENDED_SETUP to 'true'
# Useful for situations where some or all of the setup configuration is supplied prior
# to deployment time so that it is skipped in the setup wizard. This flag is primarily
# for use where K8s deployments are concerned, and it may be removed at a later date,
# as such it is not officially documented.
if ATL_BAMBOO_ENABLE_UNATTENDED_SETUP:
    setup_file=f"{BAMBOO_HOME}/unattended-setup.properties"
    gen_cfg('unattended-setup.properties.j2', setup_file, overwrite=UPDATE_CFG)
    add_jvm_arg(f"-Dbamboo.setup.settings={setup_file}")

if ATL_BAMBOO_DISABLE_AGENT_AUTH:
    add_jvm_arg('-Dbamboo.setup.remote.agent.authentication.enabled=false')

# Go
exec_app([f'{BAMBOO_INSTALL_DIR}/bin/start-bamboo.sh', '-fg'], BAMBOO_HOME,
         name='Bamboo', env_cleanup=True)
