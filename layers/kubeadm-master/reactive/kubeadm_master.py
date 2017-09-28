from subprocess import check_call, check_output
from charms.reactive import when, when_not, set_state
from charmhelpers.core import hookenv, unitdata


@when_not('kubeadm-master.deps.installed')
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
    set_state('kubeadm-master.deps.installed')

@when('kubeadm-master.deps.installed')
@when_not('kubeadm-master.initialized')
def init_master():
    cmd = ['kubeadm', 'init']
    hookenv.status_set('maintenance', 'Initializing kubernetes master')
    if not unitdata.kv().get('master.init.done', False):
        network = hookenv.config('network')
        if network == 'flannel' or network == 'canal':
            cmd.append('--pod-network-cidr=10.244.0.0/16')
        output = check_output(cmd).decode('ascii')
        unitdata.kv().set('master.init.done', output)
        unitdata.kv().flush(True)

    output = unitdata.kv().get('master.init.done')
    for line in output.split('\n'):
        if "kubeadm join --token" in line:
            print("**** {}".format(line))
            parts = line.strip().split(" ")
            unitdata.kv().set('master.token', parts[3])
            ep = parts[4].split(":")
            unitdata.kv().set('master.ip', ep[0])
            unitdata.kv().set('master.port', ep[1])
            set_state('kubeadm-master.initialized')
            return
    hookenv.status_set('error', 'Could not locate connection info')


@when('kubeadm-master.initialized')
@when_not('kubeadm-master.running')
def apply_network():
    network = hookenv.config('network')
    hookenv.status_set('maintenance', 'Installing kubernetes network {}'.format(network))
    if network == 'flannel':
        kubectl_apply('https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml')
    if network == 'canal':
        kubectl_apply('https://raw.githubusercontent.com/projectcalico/canal/master/k8s-install/1.6/rbac.yaml')
        kubectl_apply('https://raw.githubusercontent.com/projectcalico/canal/master/k8s-install/1.6/canal.yaml')

    allow_master = "kubectl --kubeconfig /etc/kubernetes/admin.conf taint nodes --all node-role.kubernetes.io/master-".split(" ")
    check_call(allow_master, shell=True)
    hookenv.status_set('active', 'Ready')
    set_state('kubeadm-master.running')


@when('kubeadm-worker.joined', 'kubeadm-master.running')
def worker_joined(worker_relation):
    token = unitdata.kv().get('master.token')
    port = unitdata.kv().get('master.port')
    ip = unitdata.kv().get('master.ip')
    worker_relation.set_ready(token, ip, port)


def kubectl_apply(what):
    apply = "kubectl --kubeconfig /etc/kubernetes/admin.conf apply -f {}".format(what)
    check_call(apply, shell=True)
