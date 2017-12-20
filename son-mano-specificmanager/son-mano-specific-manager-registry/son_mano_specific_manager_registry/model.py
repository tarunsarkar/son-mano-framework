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
This is the model of the MongoDB collection for storing SONATA's Specific Manager Registry request details.
"""

import logging
import os
from mongoengine import Document, connect, StringField, UUIDField

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("son-mano-specific-manager-registry")
LOG.setLevel(logging.INFO)


class SSMRepository(Document):
    """
    This model represents a collection for Service-Specific Manager request details.
    We use mongoengine as ORM to interact with MongoDB.
    """
    sm_repo_id = StringField(primary_key=True, required=True)
    uuid = UUIDField(required=True)
    service_name = StringField(required=True)
    version = StringField(required=True)
    description = StringField(required=False)
    specific_manager_id = StringField(required=True)
    specific_manager_type = StringField(required=True)
    sfuuid = StringField(required=False)
    function_name = StringField(required=False)
    status = StringField(required=False)
    error = StringField(required=False)

    def __repr__(self):
        return "SSMRepository(uuid=%r, service_name=%r, version=%r)" % (self.uuid, self.service_name, self.version)

    def __str__(self):
        return self.__repr__()

    def save(self, **kwargs):
        super().save(**kwargs)
        LOG.debug("Saved: %s" % self)

    def delete(self, **kwargs):
        super().delete(**kwargs)
        LOG.debug("Deleted: %s" % self)

    def to_dict(self):
        """
        Convert to dict.
        (Yes, doing it manually isn't nice but its ok with a limited number of fields and gives us more control)
        :return:
        """
        res = dict()
        # we dont need the key value (sm_repo_id) in the dictionary
        res["uuid"] = str(self.uuid)
        res["service_name"] = self.service_name
        res["version"] = self.version
        res["description"] = self.description
        res["specific_manager_id"] = self.specific_manager_id
        res["specific_manager_type"] = self.specific_manager_type
        res["sfuuid"] = self.sfuuid
        res["function_name"] = self.function_name
        res["status"] = self.status
        res["error"] = self.error
        return res


def initialize(db="son-mano-specific-manager-registry",
               host=os.environ.get("mongo_host", "127.0.0.1"),
               port=int(os.environ.get("mongo_port", 27017)),
               clear_db=True):
    db_conn = connect(db, host=host, port=port)
    LOG.info("Connected to MongoDB %r@%s:%d" % (db, host, port))
    if clear_db:
        # remove all old data from DB
        db_conn.drop_database(db)
        LOG.info("Cleared DB %r" % db)
