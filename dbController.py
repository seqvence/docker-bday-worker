import datetime
import json
import logging
import sys

import bson
from bson.json_util import dumps
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo import ReturnDocument

logging.basicConfig(level=logging.INFO, format=('%(asctime)s %(levelname)s %(message)s'))


class DbDriver():
    def __init__(self, config):
        """
        Loads configuration file into a dictionary
        Connects to Database(s)
        :return:
        """
        self.dbParam = config
        self.connect()
        self.post = dict()
        #self.cHandle = object
        #self.dbHandle = object

    def connect(self):
        """
        Connects to Database(s) and generates handlers for Database and Collection
        :return: () -> None
        """
        try:
            self.client= MongoClient(self.dbParam['hostname'],
                        int(self.dbParam['portNo']), serverSelectionTimeoutMS=5)
            self.client.server_info()
        except Exception as e:
            logging.error(e)
            sys.exit(1)
        self.dbHandle = self.client[self.dbParam['database']]
        self.cHandle = self.dbHandle[self.dbParam['collection']]

        return

    def insert_record(self, post):
        """
        Inserts a record into the Database.
        :param post: json as string
        :return: ObjectId or None
        """
        self.post = post
        try:
            self.post['submissionTime'] = str(datetime.datetime.utcnow())
            self.post['status'] = "submitted"
            post_id = self.cHandle.insert_one(self.post).inserted_id
            logging.debug(post_id)
            return post_id
        except Exception, e:
            logging.error(e)
            return None

    def retrieve_record(self, object_id):
        """
        Returns corresponding record to the ObjectId passed as param
        :param object_id: str
        :return:
        """
        try:
            response = self.cHandle.find_one({"_id": ObjectId(object_id)})
            del response['_id']
            return response
        except bson.errors.InvalidId, e:
            logging.error(e)
            return None
        except TypeError, e:
            logging.error(e)
            return None

    def get_one_record(self):
        """
        Retrieve one record with status "submitted" and updates the status to "pending"
        :return: dict
        """
        return self.cHandle.find_one_and_update({'status': 'submitted'}, {'$set': {'status': 'pending'}}, return_document=ReturnDocument.AFTER)

    def get_all_records(self):
        """
        Retrieves all documents in collection
        :return: dict
        """
        return dumps(self.cHandle.find())

    def update_record_status(self, object_id, status):
        """
        Update status for a submission record
        :param object_id: Object(object_id)
        :param status: string
        :return: None
        """
        self.cHandle.update({"_id": object_id},
                            {
                                "$set": {
                                    "status": status
                                }
                            })
        return

    def disconnect(self):
        """
        Disconnect from DB
        :return: None
        """
        self.client.close()
        return

    def _valid_json(self, data):
        """
        Parse data and load it as JSON
        :param data: string
        :return: boolean
        """
        try:
            logging.info(data)
            self.post = json.loads(data)
        except ValueError, e:
            logging.error(e)
            return False
        return True


def main():
    a = DbDriver()
    for i in range(1):
        subID = a.insert_record('{"a": "a"}')
        logging.info(a.retrieve_record(subID))
    a.disconnect()

if __name__ == '__main__':
    main()