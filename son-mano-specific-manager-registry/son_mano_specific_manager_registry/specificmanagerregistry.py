"""
Copyright (c) 2015 SONATA-NFV
ALL RIGHTS RESERVED.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Neither the name of the SONATA-NFV [, ANY ADDITIONAL AFFILIATION]
nor the names of its contributors may be used to endorse or promote
products derived from this software without specific prior written
permission.

This work has been performed in the framework of the SONATA project,
funded by the European Commission under Grant number 671517 through
the Horizon 2020 and 5G-PPP programmes. The authors would like to
acknowledge the contributions of their colleagues of the SONATA
partner consortium (www.sonata-nfv.eu).
"""
"""
This is the main module of the Specific Manager Registry component.
"""
import logging
import json
import time
import uuid
import yaml
from sonmanobase.plugin import ManoBasePlugin

from son_mano_specific_manager_registry.smr_engine import SMREngine

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("son-mano-specific-manager-registry")
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)


class SsmNotFoundException(BaseException):
    pass


class SpecificManagerRegistry(ManoBasePlugin):
    def __init__(self):

        self.name = "SMR"
        self.version = 'v0.01'
        self.description = 'Specific Manager Registry'
        self.auto_register = True
        self.wait_for_registration = True
        self.auto_heartbeat_rate = 0
        self.ssm_repo = {}

        # connect to the docker daemon
        self.smrengine = SMREngine()

        # register smr into the plugin manager
        super(SpecificManagerRegistry, self).__init__(self.name,
                                                      self.version,
                                                      self.description,
                                                      self.auto_register,
                                                      self.wait_for_registration,
                                                      self.auto_heartbeat_rate)

        LOG.info("Starting Specific Manager Registry (SMR) ...")

        # register subscriptions
        self.declare_subscriptions()

    def declare_subscriptions(self):
        """
        Declare topics to which we want to listen and define callback methods.
        """
        self.manoconn.register_async_endpoint(self.on_board, "specific.manager.registry.ssm.on-board")
        self.manoconn.register_async_endpoint(self.on_instantiate, "specific.manager.registry.ssm.instantiate")
        self.manoconn.register_async_endpoint(self.on_ssm_register, "specific.manager.registry.ssm.registration")
        self.manoconn.register_async_endpoint(self.on_ssm_update, "specific.manager.registry.ssm.update")
        self.manoconn.subscribe(self.on_ssm_triger_result, "specific.manager.registry.ssm.result")

    def on_board(self, ch, method, properties, message):

        message = yaml.load(message)
        return yaml.dump(self.smrengine.pull(ssm_uri=message['service_specific_managers'][0]['image'],
                                              ssm_name=message['service_specific_managers'][0]['id']))

    def on_instantiate(self, ch, method, properties, message):

        message = yaml.load(message)
        i_name = message['NSD']['service_specific_managers'][0]['image']
        s_name = message['NSD']['service_specific_managers'][0]['id']
        response = self.smrengine.start(image_name= i_name, ssm_name= s_name, host_ip= None)
        if response['instantiation'] == 'OK':
            self._wait_for_ssm_registration(ssm_name= s_name)
            if s_name in self.ssm_repo.keys():
                return yaml.dump({'instantiation':'OK'})
            else:
                return yaml.dump({'instantiation':'failed'})
        else:
            return yaml.dump({'instantiation': 'failed'})

    def on_ssm_register(self, ch, method, properties, message):

        message = yaml.load(str(message))
        result = {}
        keys = self.ssm_repo.keys()
        if message['name'] in keys:
            LOG.error('Cannot register SSM: %r, already exists' % message['name'])
            result = {'status': 'failed'}
        else:

            try:
                pid = str(uuid.uuid4())
                self.ssm_repo.update({message['name']: message})
                response = {
                    "status": "running",
                    "name": message['name'],
                    "version": message['version'],
                    "description": message['description'],
                    "uuid": pid,
                    "error": None
                }
                self.ssm_repo.update({message['name']: response})
                LOG.debug("SSM registration done %r" % self.ssm_repo)
                result = response
            except BaseException as ex:
                result = {'status': 'failed'}
                LOG.exception('Cannot register SSM: %r' % message['name'])
        return yaml.dump(result)


    def on_ssm_update(self, ch, method, properties, message):

        message = yaml.load(message)
        ssm_uri = message['NSD']['service_specific_managers'][0]['image']
        ssm_name = message['NSD']['service_specific_managers'][0]['id']
        host_ip = message['NSR'][1]['virtual_deployment_units'][1]['vnfc_instance'][0]['connection_points'][0]['type']['address']
        result = {}
        result.update(self.smrengine.pull(ssm_uri, ssm_name))
        result.update(self.smrengine.start(image_name= ssm_uri, ssm_name=ssm_name,  host_ip= host_ip))
        LOG.info("Waiting for ssm1_new registration ...")
        self._wait_for_ssm_registration(ssm_name=ssm_name)
        result.update(self.ssm_kill())
        if result['on-board'] == 'OK' and result['instantiation'] == 'OK' and result['status'] == 'killed':
            return yaml.dump({'update':'OK'})
        else:
            return yaml.dump({'update':'failed'})

    def ssm_kill(self):

        result = self.smrengine.stop('ssm1')
        if result == 'done':
            self.ssm_repo['ssm1']['status'] = 'killed'
            LOG.debug("%r" % self.ssm_repo)
        return {'status': self.ssm_repo['ssm1']['status']}

    def _wait_for_ssm_registration(self, ssm_name, timeout=5, sleep_interval=0.1):

        c = 0
        rep = str(self.ssm_repo)
        while ssm_name not in rep and c < timeout:
            time.sleep(sleep_interval)
            c += sleep_interval

    def on_ssm_triger_result(self, ch, method, properties, message):
        message = yaml.load(message)
        LOG.info(message['result'])

def main():
    SpecificManagerRegistry()


if __name__ == '__main__':
    main()