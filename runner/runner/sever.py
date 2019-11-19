import portalocker
import json
import os
import random
import time
import uuid

from docker import Client

from salmon.runner import exceptions
from salmon import config
from salmon.logger import log as logging

CONF = config.CONF
LOG = logging.getLogger(__name__)


def singleton(cls, *args, **kw):
    instances = {}

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return _singleton


class Remote(object):
    """
    servers's format is as follows:
    [
        {
            "id" : "uuid"
            "type": "ie|chrome|firefox",
            "version": "",
            "url": ""
        }
    ]
    """

    INIT_SERVERS_ING = False
    SERVERS_QUEUE_INITED = False
    LOCKED = False

    IDLE_SERVERS = []
    BUSY_SERVERS = []
    ALL_SERVERS = []
    CURRENT_SERVER = None

    @classmethod
    def __init__(cls):
        LOG.info("[INIT] in %s" % cls)

        @classmethod

    def init_servers(cls):

        path = CONF.browser.remote_servers_queue_json_path
        if not os.path.exists(path):
            fp = open(path, "w")
            fp.close()

        fp = open(CONF.browser.remote_servers_queue_json_path, "r+")
        portalocker.lock(fp, portalocker.LOCK_EX)

        content = fp.read()

        if content is None or content == "":
            LOG.info("init_servers-%s" % (os.getpid()))
            with open(CONF.browser.remote_servers_cfg_local_path, "r") \
                    as src_file:
                servers = json.load(src_file)
                src_file.close()
                servers_queues = {
                    "all": servers,
                    "busy": [],
                    "idle": servers,
                    "pid": os.getpid()
                }
                # json.dump(servers_queues, fp)
                fp.seek(0)
                content = json.dumps(servers_queues)
                fp.write(content)
                fp.truncate()

        else:

            servers_queues = json.loads(content)

            cls.ALL_SERVERS = servers_queues["all"]
            cls.BUSY_SERVERS = servers_queues["busy"]
            cls.IDLE_SERVERS = servers_queues["idle"]
            fp.close()

        return servers_queues

    @classmethod
    def filter_servers(cls, servers, browser_type=None, browser_version=None):
        """

        :param browser_type: ie|chrome|firefox
        :param browser_version: the version of the browser, it is used for IE browser
                        as so far
        :return:
        """
        filterd_servers = []
        for server in servers:
            server_version = server.get("version", None)
            server_type = server.get("type", None)
            if browser_type == server_type and browser_version == server_version:
                filterd_servers.append(server)

        return filterd_servers

        @classmethod

    def get_server(cls, browser_type=None, browser_version=None, user=None):

        if browser_type is None:
            raise Exception("The browser_type(%s) is invalid" % browser_type)

        # Note(liulei): if cls.CURRENT_SERVER is not None,
        # this process should be continue to use the server. But if so,
        # the server should not be released after one TestClass finished,
        # and if the concurrency is more than the count of the remote servers,
        # what will happen is that some process will never get a remote server.
        # So, after one TestClass finished, the process will release and
        # relock a new remote server, even if it may spend sometime on waitting
        # for the idle remote server.

        interval = 2
        timeout = 100
        times = int(round(timeout / interval))
        for i in range(times):
            if not cls.SERVERS_QUEUE_INITED:
                cls.init_servers()
                cls.SERVERS_QUEUE_INITED = True
            path = CONF.browser.remote_servers_queue_json_path
            # with open(path, "r+") as fp:
            fp = open(path, "r+")

            portalocker.lock(fp, portalocker.LOCK_EX)
            servers_queues = json.load(fp)

            idle_servers = servers_queues.get("idle")
            busy_servers = servers_queues.get("busy")
            all_servers = servers_queues.get("all")

            filter_idle_servers = cls.filter_servers(idle_servers, browser_type, browser_version)
            if filter_idle_servers is None or len(filter_idle_servers) == 0:
                LOG.debug("There is not exist idle server, busy server are: %s, so retrying"
                          % busy_servers)
                time.sleep(interval)
                fp.close()
                continue
            server_index = 0
            server = filter_idle_servers[server_index]
            if user:
                server["user"] = user
            cls.CURRENT_SERVER = server
            idle_servers.remove(server)
            busy_servers.append(server)
            pid = servers_queues.get("pid")

            servers_queues = {
                "all": all_servers,
                "busy": busy_servers,
                "idle": idle_servers
                # "pid": "%s,%s" % (pid, os.getpid())
            }
            LOG.debug("current all servers queues are: %s" % servers_queues)
            # json.dump(servers_queues, fp)
            fp.seek(0)
            content = json.dumps(servers_queues)
            fp.write(content)
            fp.truncate()
            cls.ALL_SERVERS = servers_queues["all"]
            cls.BUSY_SERVERS = servers_queues["busy"]
            cls.IDLE_SERVERS = servers_queues["idle"]

            fp.close()

            LOG.info("current pid and server url is: [%s]:%s,"
                     % (os.getpid(), cls.CURRENT_SERVER["url"]))
            return cls.CURRENT_SERVER
        return None

    @classmethod
    def release_server(cls, server):
        timeout = 600
        interval = 2
        times = int(round(timeout / interval))
        # with open(BrowsersConst.REMOTE_SERVERS_QUEUE_JSON_PATH, "r+") as fp:

        fp = open(CONF.browser.remote_servers_queue_json_path, "r+")
        portalocker.lock(fp, portalocker.LOCK_EX)
        servers_queues = json.load(fp)

        idle_servers = servers_queues.get("idle")
        busy_servers = servers_queues.get("busy")
        all_servers = servers_queues.get("all")
        pid = servers_queues.get("pid")

        busy_servers.remove(server)
        idle_servers.append(server)

        servers_queues = {
            "all": all_servers,
            "busy": busy_servers,
            "idle": idle_servers
            # "pid": "%s,%s" % (pid, os.getpid())
        }
        LOG.info("current pid and server url is: [%s]:%s,"
                 % (os.getpid(), cls.CURRENT_SERVER["url"]))
        # json.dump(servers_queues, fp)
        fp.seek(0)
        content = json.dumps(servers_queues)
        fp.write(content)
        fp.truncate()

        cls.BUSY_SERVERS = servers_queues.get("busy")
        cls.IDLE_SERVERS = servers_queues.get("idle")
        cls.CURRENT_SERVER = None
        fp.close()
        return True

        @classmethod

    def get_server_info(cls, server_id):
        for server in cls.ALL_SERVERS:
            if server_id == server.get("id"):
                return server
        raise Exception("Do not get the server info of id('%s')" % server_id)


class Deploy(object):
    """
    move the deploy
    """

    def __init__(self, browser_type=None, browser_version=None,
                 concurrency=None, mark=None, **kwargs):

        self.browser_type = self._get_browser_type(browser_type)
        self.browser_version = self._get_browser_version(browser_version)
        self.concurrency = self._get_browser_concurrency(concurrency)
        self.servers = None
        self.mark = mark
        self.init_servers()
        self.store_servers()

        @staticmethod

    def _get_browser_type(browser_type=None):
        if browser_type is None:
            browser_type = os.getenv(CONF.environment_name.test_browser_type)
        if browser_type is None:
            raise exceptions.BrowserTypeNotSpecifiedException()
        browser_type = browser_type.lower()
        if browser_type not in CONF.browser.supported_type:
            raise exceptions.BrowserTypeNotSupportedException(browser_type)
        return browser_type

    @staticmethod
    def _get_browser_version(browser_version=None):
        if browser_version is None:
            browser_version = os.getenv(CONF.environment_name.test_browser_version)
        if browser_version is None:
            return browser_version
        browser_version = browser_version.lower()
        # TODO: to check if the version is supported
        return browser_version

    @staticmethod
    def _get_browser_concurrency(concurrency=None):
        if concurrency is None:
            concurrency = os.getenv(CONF.environment_name.test_concurrency)

        if concurrency is None:
            raise exceptions.BrowserConcurrencyNotSpecifiedException()
        concurrency = int(concurrency)
        if concurrency == 0:
            raise exceptions.BrowserConcurrencyNotSupportedException(
                concurrency)

        return concurrency

    def init_servers(self):
        """
        get the server's config from
        :return:
        """
        self.servers = []
        remote_servers = self.get_servers_cfg_from_file()
        if remote_servers is None or len(remote_servers) == 0:
            remote_servers = self.deploy_servers()

        if remote_servers is None or len(remote_servers) == 0:
            raise exceptions.RemoteServersNotFoundError(
                "do not get any remote servers")

        self.servers = remote_servers
        Remote.IDLE_SERVERS = remote_servers
        return remote_servers

    def store_servers(self):

        # filename = "remote_servers_%s" % \
        #            "".join(random.sample(
        #                "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", 6))

        file_path = CONF.browser.remote_servers_cfg_local_path
        with open(file_path, "w") as fp:
            json.dump(self.servers, fp)
            fp.close()


    @staticmethod
    def get_servers_cfg_from_file():
        servers_cfg_path = os.getenv(CONF.environment_name.remote_servers_cfg_local_path, None)
        if servers_cfg_path is None:
            servers_cfg_path = CONF.browser.remote_servers_cfg_local_path

        if not os.path.exists(servers_cfg_path):
            LOG.info("do not found the remote servers' cfg file")
            return None

        try:
            with open(servers_cfg_path, "r") as fp:
                servers = json.load(fp)
                fp.close()
        except Exception as e:
            raise Exception("Error occur when get the servers")
        return servers

    def deploy_servers(self):


        prefix = CONF.runner.server_docker_image_prefix
        suffix = CONF.runner.server_docker_image_suffix
        if self.browser_type == "ie":
            raise Exception("The ie browser is not supported yet")

        if self.browser_version is not None:
            image = "%s%s%s:%s" % (prefix, self.browser_type, suffix, self.browser_version)
        else:
            image = "%s%s%s" % (prefix, self.browser_type, suffix)

        docker_host = CONF.runner.docker_daemon_host
        docker_port = CONF.runner.docker_daemon_port
        docker_base_url = "http://%s:%s" % (docker_host, docker_port)

        servers = []
        for i in range(self.concurrency):
            (container_info, container_id) = self.start_server_docker(
                docker_base_url=docker_base_url, image=image, browser_type=self.browser_type,
                mark=self.mark)

            bind_host, bind_vnc_port = self._get_host_port(container_info,
                                                           port=CONF.runner.vnc_port)
            bind_host, bind_port = self._get_host_port(container_info,
                                                       port=CONF.runner.selenium_port)

            server_url = "http://%s:%s/wd/hub" % (docker_host,
                                                  bind_port)
            server = {
                "id": "%s" % uuid.uuid4(),
                "type": self.browser_type,
                "version": self.browser_version,
                "url": server_url,
                "vnc_bind_port": int(bind_vnc_port),
                "bind_host": docker_host,
                "container_id": container_id
            }
            servers.append(server)

        return servers


    @staticmethod
    def _get_host_port(info, port=None):
        try:
            net_settings = info.get("NetworkSettings")
            ports = net_settings.get("Ports")
            ports = ports.get("%s/tcp" % port)

        except Exception as e:
            raise Exception("Error occured when get the port info "
                            "from the container info, the details is "
                            "as follows: %s" % e)
        if len(ports) > 1:
            raise Exception("The port(%s) is bound to multi ports(%s)" %
                            (port, ",".join(ports)))
        if len(ports) < 0:
            raise Exception("The port(%s) is not bound" % port)
        host_port = ports[0]
        port = host_port.get("HostPort")
        host = host_port.get("HostIp")
        return host, port

    def _wait_container_running(self, container_id, timeout=10, interval=2):


        times = int(round(timeout / interval))
        for i in range(times):
            container_info = self.docker_client.inspect_container(container_id)
            state = container_info.get("State")
            status = state.get("Status")
            if status == "running":
                return True

            time.sleep(interval)
        return False


    def start_server_docker(self, docker_base_url=None, image=None, browser_type=None, mark=None,
                            port=4444, **kwargs):
        name = "browser_%s_%s_%s" % (browser_type, mark, "".join(random.sample(
            "abcdefghijklmnopqrstuvwxyz0123456789", 10)))
        self.docker_client = Client(base_url=docker_base_url)
        # host_path = "%s%s" % (BrowsersConst.IMAGE_BIND_IN_HOST_PATH, name)
        host_path = CONF.runner.host_bind_dir
        bind_path = CONF.runner.container_bind_dir
        vnc_port = int(CONF.runner.vnc_port)
        volumes_binds = {
            host_path: {
                "bind": bind_path,
                "mode": "rw"
            }
        }
        container = self.docker_client.create_container(
            image=image, ports=[port, vnc_port], name=name,
            host_config=self.docker_client.create_host_config(
                port_bindings={port: None, vnc_port: None},
                binds=volumes_binds,
                privileged=True,
                shm_size="256MB")  # default shm_size is 64MB and easy to cause browser crash
        )
        c_id = container.get("Id")
        LOG.info("create container: %s" % c_id)

        response = self.docker_client.start(container=c_id)
        LOG.info("start container: %s" % response)
        self._wait_container_running(c_id)

        container_info = self.docker_client.inspect_container(c_id)
        return container_info, c_id
