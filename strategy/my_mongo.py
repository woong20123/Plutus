# import 라이브러리
from pymongo import MongoClient
import pymongo
from enum import Enum


class CollectionInfo(Enum):
    DAILY_DATA = 'daily_data_v1'
    TRADING_DAY = 'trading_day'
    VALIDATION_DATA = 'validation_data'



def get_database(database_name) :
    client = MongoClient(host='localhost', port=27017)
    db = client[database_name]
    return db


def delete_many_database(db, collect_name, match_key):
    with pymongo.timeout(30):
        if collect_name in db.list_collection_names():
            db[collect_name].delete_many(match_key)
            return
        raise Exception('collect이 확인되지 않습니다. ')

# kospi200 collection에 데이터 추가 ( upsert )
def upsert_to_database(db, collect_name, match_key, data):
    """

    :type collect_name: string
    :type data: object
    :type db: object
    :type match_key: object ex) {'date': data['date']}
    """
    with pymongo.timeout(5):
        if collect_name in db.list_collection_names():
            db[collect_name].replace_one(match_key, data, upsert=True)
            return
        raise Exception('collect이 확인되지 않습니다. ')


# 데이터 가져오기
def find_one_to_database(db: object, collect_name, query=None):
    with pymongo.timeout(5):
        if collect_name in db.list_collection_names():
            if None is query:
                return db[collect_name].find_one({})
            return db[collect_name].find_one(query)
        raise Exception('collect name이 확인되지 않습니다. ')

def find_to_database(db: object, collect_name, query=None):
    with pymongo.timeout(5):
        if collect_name in db.list_collection_names():
            if None is query:
                return db[collect_name].find({})
            return db[collect_name].find(query)
        raise Exception('collect name이 확인되지 않습니다. ')


def find_count_to_database(db: object, collect_name, query=None):
    with pymongo.timeout(5):
        if collect_name in db.list_collection_names():
            if None is query:
                return db[collect_name].count_documents({})
            return db[collect_name].count_documents(query)
        raise Exception('collect name이 확인되지 않습니다. ')


if __name__ == "__main__":
    client = MongoClient(host='localhost', port=27017)
    stock_db = client["stock"]
    stock_db['real_lion'].find_one()