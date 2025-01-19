import pytest
import os
from tinymongo import TinyMongoClient


@pytest.fixture
def collection_setup(request):
    # remove test_db if it exists
    db_name = os.path.abspath('./test_db')
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


if __name__ == '__main__':
    pytest.main()