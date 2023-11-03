import pytest
import signal
import testinfra
import xml.sax.saxutils as saxutils
import re
from helpers import get_app_home, get_app_install_dir, get_bootstrap_proc, get_procs, \
    parse_properties, parse_xml, run_image, wait_for_http_response, wait_for_proc, wait_for_log

from iterators import TimeoutIterator

PORT = 8085
STATUS_URL = f'http://localhost:{PORT}/status'


def test_jvm_args(docker_cli, image, run_user):
    environment = {
        'JVM_MINIMUM_MEMORY': '383m',
        'JVM_MAXIMUM_MEMORY': '2047m',
        'JVM_SUPPORT_RECOMMENDED_ARGS': '-verbose:gc',
    }
    container = run_image(docker_cli, image, user=run_user, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    procs_list = get_procs(container)
    jvm = [proc for proc in procs_list if get_bootstrap_proc(container) in proc][0]

    assert f'-Xms{environment.get("JVM_MINIMUM_MEMORY")}' in jvm
    assert f'-Xmx{environment.get("JVM_MAXIMUM_MEMORY")}' in jvm
    assert '-Dbamboo.setup.rss.in.docker=false' in jvm
    assert environment.get('JVM_SUPPORT_RECOMMENDED_ARGS') in jvm


def test_install_permissions(docker_cli, image):
    container = run_image(docker_cli, image)

    assert container.file(f'{get_app_install_dir(container)}/conf/server.xml').user == 'root'

    for d in ['logs', 'work', 'temp', 'conf']:
        path = f'{get_app_install_dir(container)}/{d}/'
        assert container.file(path).user == 'bamboo'


def test_first_run_state(docker_cli, image, run_user):
    container = run_image(docker_cli, image, user=run_user, ports={PORT: PORT})

    wait_for_http_response(STATUS_URL, expected_status=200)


def test_clean_shutdown(docker_cli, image, run_user):
    container = docker_cli.containers.run(image, detach=True, user=run_user, ports={PORT: PORT})
    host = testinfra.get_host("docker://" + container.id)

    wait_for_http_response(STATUS_URL, expected_status=200)

    container.kill(signal.SIGTERM)

    end = r'org\.apache\.coyote\.AbstractProtocol\.destroy Destroying ProtocolHandler'
    wait_for_log(container, end)


def test_shutdown_script(docker_cli, image, run_user):
    container = docker_cli.containers.run(image, detach=True, user=run_user, ports={PORT: PORT})
    host = testinfra.get_host("docker://" + container.id)

    wait_for_http_response(STATUS_URL, expected_status=200)

    container.exec_run('/shutdown-wait.sh')

    end = r'org\.apache\.coyote\.AbstractProtocol\.destroy Destroying ProtocolHandler'
    wait_for_log(container, end)


def test_server_xml_defaults(docker_cli, image):
    container = run_image(docker_cli, image)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/conf/server.xml')
    connector = xml.find('.//Connector')
    context = xml.find('.//Context')
    valve = xml.find('.//Valve[@className="org.apache.catalina.valves.AccessLogValve"]')

    assert connector.get('port') == '8085'
    assert connector.get('maxThreads') == '150'
    assert connector.get('minSpareThreads') == '25'
    assert connector.get('connectionTimeout') == '20000'
    assert connector.get('enableLookups') == 'false'
    assert connector.get('protocol') == 'HTTP/1.1'
    assert connector.get('acceptCount') == '100'
    assert connector.get('secure') == 'false'
    assert connector.get('scheme') == 'http'
    assert connector.get('proxyName') == ''
    assert connector.get('proxyPort') == ''

    assert context.get('path') == ''
    assert valve.get('maxDays') == '-1'

def test_server_xml_catalina_fallback(docker_cli, image):
    environment = {
        'CATALINA_CONNECTOR_PROXYNAME': 'PROXYNAME',
        'CATALINA_CONNECTOR_PROXYPORT': 'PROXYPORT',
        'CATALINA_CONNECTOR_SECURE': 'SECURE',
        'CATALINA_CONNECTOR_SCHEME': 'SCHEME',
        'CATALINA_CONTEXT_PATH': 'CONTEXT'
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/conf/server.xml')
    connector = xml.find('.//Connector')
    context = xml.find('.//Context')

    assert connector.get('proxyName') == 'PROXYNAME'
    assert connector.get('proxyPort') == 'PROXYPORT'
    assert connector.get('scheme') == 'SCHEME'
    assert connector.get('secure') == 'SECURE'
    assert context.get('path') == 'CONTEXT'


def test_server_xml_params(docker_cli, image):
    environment = {
        'ATL_TOMCAT_MGMT_PORT': '8008',
        'ATL_TOMCAT_PORT': '9095',
        'ATL_TOMCAT_MAXTHREADS': '151',
        'ATL_TOMCAT_MINSPARETHREADS': '26',
        'ATL_TOMCAT_CONNECTIONTIMEOUT': '20001',
        'ATL_TOMCAT_ENABLELOOKUPS': 'true',
        'ATL_TOMCAT_PROTOCOL': 'HTTP/1.1',
        'ATL_TOMCAT_ACCEPTCOUNT': '101',
        'ATL_TOMCAT_SECURE': 'true',
        'ATL_TOMCAT_SCHEME': 'https',
        'ATL_PROXY_NAME': 'bamboo.atlassian.com',
        'ATL_PROXY_PORT': '443',
        'ATL_TOMCAT_CONTEXTPATH': '/mybamboo',
        'ATL_TOMCAT_ACCESS_LOGS_MAXDAYS': '10',
        'ATL_TOMCAT_COMPRESSION': 'on',
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/conf/server.xml')
    connector = xml.find('.//Connector')
    context = xml.find('.//Context')
    valve = xml.find('.//Valve[@className="org.apache.catalina.valves.AccessLogValve"]')

    assert xml.get('port') == environment.get('ATL_TOMCAT_MGMT_PORT')

    assert connector.get('port') == environment.get('ATL_TOMCAT_PORT')
    assert connector.get('maxThreads') == environment.get('ATL_TOMCAT_MAXTHREADS')
    assert connector.get('minSpareThreads') == environment.get('ATL_TOMCAT_MINSPARETHREADS')
    assert connector.get('connectionTimeout') == environment.get('ATL_TOMCAT_CONNECTIONTIMEOUT')
    assert connector.get('enableLookups') == environment.get('ATL_TOMCAT_ENABLELOOKUPS')
    assert connector.get('protocol') == environment.get('ATL_TOMCAT_PROTOCOL')
    assert connector.get('acceptCount') == environment.get('ATL_TOMCAT_ACCEPTCOUNT')
    assert connector.get('secure') == environment.get('ATL_TOMCAT_SECURE')
    assert connector.get('scheme') == environment.get('ATL_TOMCAT_SCHEME')
    assert connector.get('proxyName') == environment.get('ATL_PROXY_NAME')
    assert connector.get('proxyPort') == environment.get('ATL_PROXY_PORT')
    assert connector.get('compression') == environment.get('ATL_TOMCAT_COMPRESSION')
    assert connector.get('compressibleMimeType') == 'text/html,text/xml,text/plain,text/css,text/javascript,application/javascript,application/json,application/xml'
    assert connector.get('compressionMinSize') == '2048'

    assert context.get('path') == environment.get('ATL_TOMCAT_CONTEXTPATH')
    
    assert valve.get('maxDays') == environment.get('ATL_TOMCAT_ACCESS_LOGS_MAXDAYS')


def test_pre_seed_file(docker_cli, image, run_user):
    environment = {
        'ATL_BAMBOO_ENABLE_UNATTENDED_SETUP': 'True',
        'ATL_DB_TYPE': 'postgresql',
        'ATL_JDBC_URL': 'jdbc:postgresql://172.17.0.2:5432/bamboodocker',
        'ATL_JDBC_USER':  "dbuser",
        'ATL_JDBC_PASSWORD':  "dbpass",
        'ATL_IMPORT_OPTION': 'import',
        'ATL_IMPORT_PATH': '/my/import/path',
        'ATL_LICENSE': 'MYLICENSE',
        'ATL_ADMIN_USERNAME': 'adminuser',
        'ATL_ADMIN_PASSWORD': 'adminpass',
        'ATL_ADMIN_FULLNAME': 'adminname',
        'ATL_ADMIN_EMAIL': 'admin@atlassian.com'
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    props = container.file(f'{get_app_home(container)}/unattended-setup.properties')

    assert props.contains("db.type=postgresql")
    assert props.contains('db.user=dbuser')
    assert props.contains('db.password=dbpass')
    assert props.contains('db.url=jdbc:postgresql://172.17.0.2:5432/bamboodocker')

    assert props.contains('bamboo.import.option=import')
    assert props.contains('bamboo.import.path=/my/import/path')

    assert props.contains('bamboo.license=MYLICENSE')

    assert props.contains('bamboo.admin.username=adminuser')
    assert props.contains('bamboo.admin.fullname=adminname')
    assert props.contains('bamboo.admin.password=adminpass')
    assert props.contains('bamboo.admin.email=admin@atlassian.com')

def test_pre_seed_file_broker_uri_nio(docker_cli, image, run_user):
    environment = {
        'ATL_BAMBOO_ENABLE_UNATTENDED_SETUP': 'True',
        'BAMBOO_VERSION': '9.1.2'
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    props = container.file(f'{get_app_home(container)}/unattended-setup.properties')

    assert props.contains("bamboo.broker.uri=nio://0.0.0.0:54663")

def test_pre_seed_file_broker_uri_ssl_two_three(docker_cli, image, run_user):
    environment = {
        'ATL_BAMBOO_ENABLE_UNATTENDED_SETUP': 'True',
        'BAMBOO_VERSION': '9.2.3'
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    props = container.file(f'{get_app_home(container)}/unattended-setup.properties')

    assert props.contains("bamboo.broker.uri=ssl://0.0.0.0:54663")

def test_pre_seed_file_broker_uri_ssl_three_one(docker_cli, image, run_user):
    environment = {
        'ATL_BAMBOO_ENABLE_UNATTENDED_SETUP': 'True',
        'BAMBOO_VERSION': '9.3.1'
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    props = container.file(f'{get_app_home(container)}/unattended-setup.properties')

    assert props.contains("bamboo.broker.uri=ssl://0.0.0.0:54663")

def test_pre_seed_file_broker_uri_ssl_three_one_plus(docker_cli, image, run_user):
    environment = {
        'ATL_BAMBOO_ENABLE_UNATTENDED_SETUP': 'True',
        'BAMBOO_VERSION': '9.3.3'
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    props = container.file(f'{get_app_home(container)}/unattended-setup.properties')

    assert props.contains("bamboo.broker.uri=ssl://0.0.0.0:54663")

def test_bamboo_cfg_xml(docker_cli, image):
    environment = {
        'BUILD_NUMBER': '61009',
        'ATL_JDBC_URL': 'jdbc:postgresql://172.17.0.2:5432/bamboodocker',
        'ATL_BROKER_CLIENT_URI': 'failover:(tcp://fa802b2849c3:54664?wireFormat.maxInactivityDuration=300000)?maxReconnectAttempts=10&amp;initialReconnectDelay=15000',
        'ATL_BROKER_URI': 'nio://0.0.0.0:54664',
        'ATL_DB_POOLMINSIZE': '4',
        'ATL_DB_POOLMAXSIZE': '400',
        'ATL_DB_TIMEOUT': '40',
        'ATL_DB_CONNECTIONTIMEOUT': '60',
        'ATL_DB_LEAKDETECTION': '20'
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_home(container)}/bamboo.cfg.xml')

    assert xml.find(".//buildNumber").text == environment.get('BUILD_NUMBER')
    assert saxutils.escape(xml.find(".//property[@name='bamboo.jms.broker.client.uri']").text) == environment.get(
        'ATL_BROKER_CLIENT_URI')
    assert xml.find(".//property[@name='bamboo.jms.broker.uri']").text == environment.get('ATL_BROKER_URI')
    assert xml.find(".//property[@name='hibernate.hikari.maximumPoolSize']").text == environment.get(
        'ATL_DB_POOLMAXSIZE')
    assert xml.find(".//property[@name='hibernate.hikari.minimumIdle']").text == environment.get('ATL_DB_POOLMINSIZE')
    assert xml.find(".//property[@name='hibernate.hikari.idleTimeout']").text == str(
        int(environment.get('ATL_DB_TIMEOUT')) * 1000)
    assert xml.find(".//property[@name='hibernate.hikari.connectionTimeout']").text == str(
        int(environment.get('ATL_DB_CONNECTIONTIMEOUT')) * 1000)
    assert xml.find(".//property[@name='hibernate.hikari.leakDetectionThreshold']").text == str(
        int(environment.get('ATL_DB_LEAKDETECTION')) * 1000)


def test_skip_bamboo_cfg_xml(docker_cli, image):
    environment = {
        'BUILD_NUMBER': '61009',
        'ATL_JDBC_URL': 'jdbc:postgresql://172.17.0.2:5432/bamboodocker',
        'ATL_BROKER_CLIENT_URI': 'failover:(tcp://fa802b2849c3:54664?wireFormat.maxInactivityDuration=300000)?maxReconnectAttempts=10&amp;initialReconnectDelay=15000',
        'ATL_BROKER_URI': 'nio://0.0.0.0:54664',
        'ATL_DB_POOLMINSIZE': '4',
        'ATL_DB_POOLMAXSIZE': '400',
        'ATL_DB_TIMEOUT': '40',
        'ATL_BAMBOO_SKIP_CONFIG': 'True'
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    assert not container.file(f'{get_app_home(container)}/bamboo.cfg.xml').exists


def test_seraph_defaults(docker_cli, image):
    container = run_image(docker_cli, image)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/atlassian-bamboo/WEB-INF/classes/seraph-config.xml')
    # param = xml.findall('//param-name[text()="autologin.cookie.age"]') == []
    param = xml.findall('.//param-name[.="autologin.cookie.age"]') == []


def test_seraph_login_set(docker_cli, image):
    container = run_image(docker_cli, image, environment={"ATL_AUTOLOGIN_COOKIE_AGE": "TEST_VAL"})
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/atlassian-bamboo/WEB-INF/classes/seraph-config.xml')
    assert xml.findall('.//param-value[.="TEST_VAL"]')[0].text == "TEST_VAL"


def test_bamboo_init_set(docker_cli, image):
    container = run_image(docker_cli, image, environment={'BAMBOO_HOME': '/tmp/'})
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    init = container.file(f'{get_app_install_dir(container)}/atlassian-bamboo/WEB-INF/classes/bamboo-init.properties')
    assert init.contains("bamboo.home = /tmp/")


def test_java_in_run_user_path(docker_cli, image):
    RUN_USER = 'bamboo'
    container = run_image(docker_cli, image)
    proc = container.run(f'su -c "which java" {RUN_USER}')
    assert len(proc.stdout) > 0


def test_non_root_user(docker_cli, image):
    RUN_UID = 2005
    RUN_GID = 2005
    container = run_image(docker_cli, image, user=f'{RUN_UID}:{RUN_GID}')
    jvm = wait_for_proc(container, "org.apache.catalina.startup.Bootstrap")


def test_bamboo_cfg_xml_overwrite(docker_cli, image, run_user):
    environment = {
        'BUILD_NUMBER': '61009',
        'ATL_FORCE_CFG_UPDATE': 'y',
    }
    container = docker_cli.containers.run(image, detach=True, user=run_user, environment=environment)
    tihost = testinfra.get_host("docker://"+container.id)
    _jvm = wait_for_proc(tihost, get_bootstrap_proc(tihost))
    cfg = f'{get_app_home(tihost)}/bamboo.cfg.xml'

    xml = parse_xml(tihost, cfg)
    assert xml.find(".//buildNumber").text == "61009"

    container.exec_run(f"sed -i 's/61009/99999/' {cfg}")

    xml = parse_xml(tihost, cfg)
    assert xml.find(".//buildNumber").text == "99999"

    container.stop(timeout=60)
    container.start()
    _jvm = wait_for_proc(tihost, get_bootstrap_proc(tihost))

    xml = parse_xml(tihost, cfg)
    assert xml.find(".//buildNumber").text == "61009"


def test_pre_seed_file_no_overwrite(docker_cli, image, run_user):
    environment = {
        'ATL_BAMBOO_ENABLE_UNATTENDED_SETUP': 'True',
        'ATL_JDBC_USER':  "dbuser",
    }
    container = docker_cli.containers.run(image, detach=True, user=run_user, environment=environment)
    tihost = testinfra.get_host("docker://"+container.id)
    _jvm = wait_for_proc(tihost, get_bootstrap_proc(tihost))

    cfg = f'{get_app_home(tihost)}/unattended-setup.properties'

    props = tihost.file(cfg)
    assert props.contains('db.user=dbuser')

    container.exec_run(f"sed -i 's/dbuser/differentuser/' {cfg}")

    props = tihost.file(cfg)
    assert props.contains('db.user=differentuser')

    container.stop(timeout=60)
    container.start()
    _jvm = wait_for_proc(tihost, get_bootstrap_proc(tihost))

    props = tihost.file(cfg)
    assert props.contains('db.user=differentuser')

def test_pre_seed_file_overwrite(docker_cli, image, run_user):
    environment = {
        'ATL_BAMBOO_ENABLE_UNATTENDED_SETUP': 'True',
        'ATL_JDBC_USER':  "dbuser",
        'ATL_FORCE_CFG_UPDATE': 'y',
    }
    container = docker_cli.containers.run(image, detach=True, user=run_user, environment=environment)
    tihost = testinfra.get_host("docker://"+container.id)
    _jvm = wait_for_proc(tihost, get_bootstrap_proc(tihost))

    cfg = f'{get_app_home(tihost)}/unattended-setup.properties'

    props = tihost.file(cfg)
    assert props.contains('db.user=dbuser')

    container.exec_run(f"sed -i 's/dbuser/differentuser/' {cfg}")

    props = tihost.file(cfg)
    assert props.contains('db.user=differentuser')

    container.stop(timeout=60)
    container.start()
    _jvm = wait_for_proc(tihost, get_bootstrap_proc(tihost))

    props = tihost.file(cfg)
    assert props.contains('db.user=dbuser')

def test_git(docker_cli, image, run_user):
    container = run_image(docker_cli, image, user=run_user)
    container.run_test('git --version')
    container.run_test('git-lfs --version')
    container.run_test('git lfs --version')
    gitconfig = container.check_output('git config --system --list')
    assert 'filter.lfs' in gitconfig
    assert 'error' not in gitconfig

def test_skip_default_allowlist_secure_vars(docker_cli, image, run_user):
    environment = {
        'AWS_WEB_IDENTITY_TOKEN_FILE': '/path/to/file',
        'com_atlassian_db_config_password_ciphers_algorithm_javax_crypto_foor_bar': '/path/to/file'
    }
    container = docker_cli.containers.run(image, detach=True, user=run_user, environment=environment,
                                          ports={PORT: PORT})
    wait_for_http_response(STATUS_URL, expected_status=200)
    rpat = re.compile(r'Unsetting environment var (AWS_WEB_IDENTITY_TOKEN_FILE|com_atlassian_db_config_password_ciphers_algorithm_javax_crypto_foor_bar)')
    logs = container.logs(stream=True, follow=True)
    li = TimeoutIterator(logs, timeout=1)
    for line in li:
        if line == li.get_sentinel():
            return
        line = line.decode('UTF-8')
        if rpat.search(line):
            print(line)
            raise EOFError(f"Found unexpected log line")

def test_skip_custom_allowlist_secure_vars(docker_cli, image, run_user):
    environment = {
        'MY_TOKEN': 'tokenvalue',
        'SECRET': 'secretvalue',
        'MY_PASS': 'passvalue',
        'ATL_ALLOWLIST_SENSITIVE_ENV_VARS': 'MY_TOKEN, MY_PASS',
    }
    container = docker_cli.containers.run(image, detach=True, user=run_user, environment=environment, ports={PORT: PORT})
    wait_for_http_response(STATUS_URL, expected_status=200)

    # ensure SECRET env var is unset
    var_unset_log_line_secret = 'Unsetting environment var SECRET'
    wait_for_log(container, var_unset_log_line_secret)

    # ensure MY_TOKEN and MY_PASS are not unset as they are in the whitelist
    rpat = re.compile(r'Unsetting environment var (MY_TOKEN|MY_PASS)')
    logs = container.logs(stream=True, follow=True)
    li = TimeoutIterator(logs, timeout=1)
    for line in li:
        if line == li.get_sentinel():
            return
        line = line.decode('UTF-8')
        if rpat.search(line):
            print(line)
            raise EOFError(f"Found unexpected log line")
