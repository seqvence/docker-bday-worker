import datetime
import json
import logging
import sys
import urllib
import random

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
        self.dbParam = config.database
        self.connect()
        self.post = dict()
        self.twitter_link = config.twitter['tweet_link']
        self.twitter_message = urllib.quote(config.twitter['tweet_message'])

    def connect(self):
        """
        Connects to Database(s) and generates handlers for Database and Collection
        :return: () -> None
        """
        try:
            self.client = MongoClient('mongodb://' +
                                      self.dbParam['username'] + ':' +
                                      self.dbParam['password'] + '@' +
                                      self.dbParam['hostname'] + ':' +
                                      self.dbParam['portNo'] +
                                      '/?replicaSet=' +
                                      self.dbParam['replicaSet']
                                      )
            self.client.server_info()
        except Exception as e:
            logging.error(e)
            sys.exit(1)
        self.dbHandle = self.client[self.dbParam['database']]
        self.cHandle = self.dbHandle[self.dbParam['collection']]
        self.sHandle = self.dbHandle[self.dbParam['collection_stats']]

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
        return self.cHandle.find_one_and_update({'status': 'submitted'}, {'$set': {'status': 'pending'}},
                                                return_document=ReturnDocument.AFTER)

    def get_all_records(self):
        """
        Retrieves all documents in collection
        :return: dict
        """
        return dumps(self.cHandle.find())

    def update_record_status(self, object_id, status, statusmsg=None):
        """
        Update status for a submission record
        :param statusmsg: string
        :param object_id: Object(object_id)
        :param status: string
        :return: None
        """
        update_struct = {
                            "$set": {
                                "status": status
                            }
                        }
        if statusmsg:
            update_struct['$set']['statusmsg'] = statusmsg
        if status == "successful" and self.has_twitter(object_id):
            update_struct['$set']['tweetmsg'] = self.twitter_link + self.twitter_message

        self.cHandle.update({"_id": object_id}, update_struct)
        return

    def update_record_location(self, object_id, lat, lng):
        if self.cHandle.find_one({"coordinates": {"lat": lat, "lng": lng}}):
            lat *= random.uniform(0.00001, 1.00001) * 0.00005 + 0.99999
            lng *= random.uniform(0.00001, 1.00001) * 0.0005 + 0.9999
        self.cHandle.update({"_id": object_id},
                            {
                                "$set": {
                                    "coordinates": {"lat": lat, "lng": lng}
                                }
                            })
        return

    def has_twitter(self, object_id):
        """
        Check if submission has Twitter handler
        :param object_id: objectId
        :return: boolean
        """
        return "twitter" in self.cHandle.find_one({"_id": ObjectId(object_id)})

    def get_twitter(self, object_id):
        """
        Retrieve Twitter handler
        :param object_id: objectId
        :return: string
        """
        return self.cHandle.find_one({"_id": ObjectId(object_id)}, {"_id": False, "twitter": True})['twitter']

    def disconnect(self):
        """
        Disconnect from DB
        :return: None
        """
        self.client.close()
        return

    def no_of_submissions(self):
        '''
        Returns the number of submissions pending validation
        :return:
        '''
        return self.cHandle.count({"status": "submitted"})

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
    import app_config as config2
    a = DbDriver(config2)
    print a
    # for i in range(1):
    #     subID = a.insert_record('{"a": "a"}')
    #     logging.info(a.retrieve_record(subID))
    # print a.update_record_status(ObjectId('56ce3b9b200b7e211a45c8f3'), status="successful")
    #a.update_record_location(ObjectId('56debd3b200b7e02e70b90e0'), 1.00, 2.00)
    a.disconnect()

if __name__ == '__main__':
    main()