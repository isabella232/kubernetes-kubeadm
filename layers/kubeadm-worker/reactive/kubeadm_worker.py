from subprocess import check_call
from charms.reactive import when, when_not, set_state
from charmhelpers.core import hookenv


@when_not('kubeadm-worker.deps.installed')
def install_kubeadm_deps():
    hookenv.status_set('maintenance', 'Installing kubernetes binaries')
    add_key = ['/bin/bash', '-c', 'curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -']
    check_call(add_key)
    repo = "deb http://apt.kubernetes.io/ kubernetes-xenial main"
    with(open('/etc/apt/sources.list.d/kubernetes.list', 'w+')) as stream:
        stream.write(repo)
    apt_update = "apt-get update".split(" ")
    check_call(apt_update)
    apt_install = "apt-get install -y kubelet kubeadm kubectl".split(" ")
    check_call(apt_install)
    set_state('kubeadm-worker.deps.installed')
    hookenv.status_set('blocked', 'Waiting for connection to a master')


@when('kubeadm-worker.deps.installed', 'kubeadm-master.ready')
@when_not('kubeadm-worker.initialized')
def init_worker(master):
    hookenv.status_set('maintenance', 'Connecting to master')
    master = master.get_connection_info()
    cmd = ['kubeadm', 'join', '--token', master["token"], "{}:{}".format(master['ip'], master['port'])]
    hookenv.status_set('maintenance', 'Initializing kubernetes worker')
    check_call(cmd)
    hookenv.status_set('active', 'Ready - connected to master {}'.format(master["ip"]))
    set_state('kubeadm-worker.initialized')
