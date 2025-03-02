import pytest
import os
from tinymongo import TinyMongoClient


@pytest.fixture
def collection_setup(request):
    # remove test_db if it exists
    db_name = os.path.abspath('../test_db')
    try:
        for f in os.listdir(os.path.join('.', db_name)):
            print('removing file ', f)
            os.remove(os.path.join(db_name, f))
        if len(os.listdir(db_name)) == 0:
            os.rmdir(db_name)
    except OSError:
        pass

    # insert some test data

    tiny_client = TinyMongoClient(db_name)
    tiny_database = tiny_client.tinyDatabase
    tiny_collection = tiny_database.tinyCollection
    tiny_collection.delete_many({})  # should delete all records in the collection

    def fin():
        tiny_client.close()

    yield tiny_collection, tiny_database, tiny_client
    request.addfinalizer(finalizer=fin)

    return tiny_database

def test_collection_name_list(collection_setup):
    database = collection_setup[1]
    tabs = database.collection_names()
    assert "tinyCollection" in tabs
    assert "_default" in tabs

def test_get_collection(collection_setup):
    database = collection_setup[1]
    collection = getattr(database, "tinyCollection")
    assert True

def test_delete_many(collection_setup):
    collection = collection_setup[0]
    delete_many_result = collection.delete_many({"username": "user1"})
    print(delete_many_result.deleted_count)
    print(delete_many_result.raw_result)
    assert True

def test_insert_many(collection_setup):
    collection = collection_setup[0]
    test_data = [
        {"username": "user1", "password": "password1"},
        {"username": "user2", "password": "password2"},
        {"username": "user3", "password": "password3"}
    ]
    insert_many_result = collection.insert_many(test_data)
    print(insert_many_result.inserted_ids)
    print(insert_many_result.eids)
    assert True

def test_query(collection_setup):
    collection = collection_setup[0]
    test_data = [
        {"username": "user1", "password": "password4"},
    ]
    insert_many_result = collection.insert_many(test_data)
    query_result = collection.find({"username": "user1"})
    query_result_length = query_result.count()
    query_result_list = [query_result[i] for i in range(query_result_length)]
    print(query_result_list)
    assert True

def test_insert_query_dbs(collection_setup):

    required_databases = [
        "admin.database",
        "admin.system",
        "config.system",
        "local.startup_log",
    ]
    for db_str in required_databases:
        database_strs = db_str.split(".")
        collection_name, table_name = database_strs
        # the database will be created automatically when we access it if it doesn't exist
        collection = getattr(collection_setup[2], collection_name)
        table = getattr(collection, table_name)
        table.find()
    admin_table = collection_setup[2].admin.database
    created_dbs = [
        {"name": "config"},
        {"name": "local"}
    ]
    admin_table.insert_many(created_dbs)
    # ============== find all method 1
    query_result = admin_table.find()
    db_num = admin_table.count()
    query_result_list = [query_result[i] for i in range(db_num)]
    print(query_result_list)
    config_db = getattr(collection_setup[2], query_result_list[0]["name"])
    assert db_num == 2
    assert "system" in config_db.collection_names()
    # ============== find all method 2
    # query_result = admin_table.find(filter={"name":1, "_id": 0})
    # db_num = admin_table.count()
    # query_result_list = [query_result[i] for i in range(db_num)]
    # print(query_result_list)
    # assert db_num == 3


if __name__ == '__main__':
    pytest.main()