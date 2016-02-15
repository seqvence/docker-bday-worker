__author__ = 'valentinstoican'

import datetime
import json
import logging
import sys

import bson
from bson.objectid import ObjectId
from bson.json_util import dumps
from pymongo import MongoClient
from pymongo import ReturnDocument

logging.basicConfig(level=logging.INFO, format=('%(asctime)s %(levelname)s %(message)s'))

class dbDriver():
    def __init__(self, config):
        '''
        Loads configuration file into a dictionary
        Connects to Database(s)
        :return:
        '''
        self.dbParam = config
        self.connect()
        self.post = dict()


    def connect(self):
        '''
        Connects to Database(s) and generates handlers for Database and Collection
        :return: () -> None
        '''
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


    def insertRecord(self,post):
        '''
        Inserts a record into the Database.
        :param post: json as string
        :return: ObjectId or None
        '''
        self.post = post
        try:
            self.post['submissionTime'] = str(datetime.datetime.utcnow())
            self.post['status'] = "submitted"
            post_id = self.cHandle.insert_one(self.post).inserted_id
            logging.debug(post_id)
            return post_id
        except Exception,e:
            logging.error(e)
            return None

    def retrieveRecord(self,id):
        '''
        Returns corresponding record to the ObjectId passed as param
        :param id: str
        :return:
        '''
        try:
            response = self.cHandle.find_one({"_id": ObjectId(id)})
            del response['_id']
            return response
        except bson.errors.InvalidId, e:
            logging.error(e)
            return None
        except TypeError,e:
            logging.error(e)
            return None

    def getOneRecord(self):
        '''
        Retrieve one record with status "submitted" and updates the status to "pending"
        :return: dict
        '''
        return self.cHandle.find_one_and_update({'status': 'submitted'}, {'$set': {'status': 'pending'}}, return_document=ReturnDocument.AFTER)

    def getAllRecords(self):
        '''
        Retrieves all documents in collection
        :return: dict
        '''
        return dumps(self.cHandle.find())

    def update_record_status(self, id, status):
        self.cHandle.update({"_id": id},
                            {
                                "$set": {
                                    "status": status
                                },
                                "$currentDate": {"lastModified": True}
                            })

    def disconnect(self):
        self.client.close()
        return

    def _validJson(self,data):
        try:
            logging.info(data)
            self.post = json.loads(data)
        except ValueError, e:
            logging.error(e)
            return False
        return True

def main():
    a = dbDriver()
    for i in range(1):
        subID = a.insertRecord('{"a": "a"}')
        logging.info(a.retrieveRecord(subID))
    a.disconnect()

if __name__ == '__main__':
    main()