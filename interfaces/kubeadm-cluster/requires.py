# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from charms.reactive import RelationBase
from charms.reactive import hook
from charms.reactive import scopes


class KubeadmRequires(RelationBase):
    scope = scopes.GLOBAL

    def is_ready(self):
        return self.get_remote('ready', 'false').lower() == 'true'

    @hook('{requires:kubeadm-cluster}-relation-joined')
    def joined(self):
        conv = self.conversation()
        conv.set_state('{relation_name}.joined')

    @hook('{requires:kubeadm-cluster}-relation-changed')
    def changed(self):
        conv = self.conversation()
        if self.is_ready():
            conv.set_state('{relation_name}.ready')

    @hook('{requires:kubeadm-cluster}-relation-departed')
    def departed(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.joined')
        conv.remove_state('{relation_name}.ready')

    def get_connection_info(self):
        conv = self.conversation()
        token = conv.get_remote('token')
        ip = conv.get_remote('ip')
        port = conv.get_remote('port')
        return {"ip": ip, "port": port, "token": token}
