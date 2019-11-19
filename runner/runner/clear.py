import os
import json

from docker import Client
from salmon.runner import exceptions
from salmon.logger import log as logging
from salmon import config

CONF = config.CONF
LOG = logging.getLogger(__name__)


def get_container_id():
    servers_cfg_file_path = CONF.browser.remote_servers_cfg_local_path
    if servers_cfg_file_path is None:
        raise exceptions.RemoteServersNotFoundError("don't get servers_cfg_file")
    else:
        with open(servers_cfg_file_path, "r") as fp:
            servers_cfg = json.load(fp)
            fp.close()
        c_id = []
        for single_cfg in servers_cfg:
            a = single_cfg['container_id']
            c_id.append(a)
        return c_id


def del_container_by_id():
    docker_client = Client(base_url=docker_base_url)
    container_id = get_container_id()
    for c_id in container_id:
        docker_client.remove_container(c_id, force=True)
    return container_id


def del_servers_cfg_file():
    cfg_file_path = CONF.browser.remote_servers_cfg_local_path
    if os.path.exists(cfg_file_path):
        try:
            os.remove(cfg_file_path)
        except Exception as e:
            LOG.error(e)
    else:
        LOG.info('no such file:%s' % cfg_file_path)


if __name__ == "__main__":
    docker_host = CONF.runner.docker_daemon_host
    docker_port = CONF.runner.docker_daemon_port
    docker_base_url = "http://%s:%s" % (docker_host, docker_port)
    container_id = del_container_by_id()
    for i in container_id:
        LOG.info("delete chromdocker(id:%s) success!" % i)
    del_servers_cfg_file()