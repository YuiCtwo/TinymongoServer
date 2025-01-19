import struct
import bson

from utils.logger import server_logger
from protocol.mongodb.op_code import OpCode

def arry2flag(arr):
    """
    Convert byte like `00011000` stored in array to integer. Used for responseFlags
    :param arr: length<=32, every element is 0 or 1 represents a bit.
    :return: integer of responseFlags
    """
    result = 0
    for idx, one in enumerate(arr):
        result += (int(one) << idx)
    return result


def byte2string(data, offset):
    """
    Convert byte data to string.
    :param data: byte data
    :param offset: pointer to the start of the string
    :return: pointer to the end of the string and the string
    """
    full_str = ""
    # cstring end with b'\0'
    while data[offset] != 0:
        full_str += chr(data[offset])
        offset += 1
    return offset+1, full_str

def byte2document(data, offset):
    """
    Covert byte data to dict object in Python
    :param data: byte data
    :param offset: pointer to the start of the document
    :return: offset and decoded document result
    """
    doc_length = struct.unpack("<i", data[offset: offset+4])[0]
    document = bson.loads(data[offset: offset+doc_length])
    offset += doc_length
    return document, offset

class HeadHandler:

    def do_parse(self, data):
        # MongoDB message header
        # 16 bytes in total, 4 bytes each: (message length), (request id), (response to), (op code)
        header = struct.unpack("<iiii", data[:16])
        return {
            "message_length": header[0],
            "request_id": header[1],
            "response_to": header[2],
            "op_code": header[3]
        }


class MongoDBHandler:
    def __init__(self):
        self.logger = server_logger
        self.op_code = OpCode.OP_DUMMY
        self.supported_version = 0.0

    def do_parse(self, data):
        """
        :param data: raw data received from client
        :return: json object contains the request payload
        """
        # DO NOT USE THIS METHOD, IT IS JUST A PLACEHOLDER
        return bson.loads(data[16:])

    def do_handle(self, payload: dict, backend) -> dict:
        """
        :param payload: json object contains the request payload
        :param backend: a collection object in TinyMongo
        :return: response payload in json object
        """
        # if no response required, return empty dict
        return {}

class CompressedHandler(MongoDBHandler):
    pass

class MSGHandler(MongoDBHandler):
    pass

class InsertHandler(MongoDBHandler):

    def __init__(self):
        super().__init__()
        self.op_code = OpCode.OP_INSERT
        self.supported_version = 5.0

    def do_parse(self, data):
        offset = 16
        flag = struct.unpack("<i", data[offset:offset+4])[0]
        offset += 4
        full_collection_name, offset = byte2string(data, offset)
        documents = []
        while offset < len(data):
            document, offset = byte2document(data, offset)
            documents.append(document)

        return {
            "flags": flag,
            "fullCollectionName": full_collection_name,
            "documents": documents
        }


    def do_handle(self, payload: dict, backend) -> dict:
        self.logger.info(f"Insert Operation: {payload}")
        flags = payload["flags"]
        
        full_collection_name = payload["fullCollectionName"]
        # collection_name like "db.collection"
        db_name, table_name = full_collection_name.split(".")
        collection = getattr(backend, db_name)
        table = getattr(collection, table_name)
        documents = payload["documents"]
        record_id = table.insert_multiple(documents)
        return {}


class UpdateHandler(MongoDBHandler):
    pass

class DeleteHandler(MongoDBHandler):
    pass

class GetMoreHandler(MongoDBHandler):
    pass

class KillCursorsHandler(MongoDBHandler):
    pass

class QueryHandler(MongoDBHandler):
    def __init__(self):
        super().__init__()
        self.op_code = OpCode.OP_QUERY
        self.supported_version = 5.0

    def do_parse(self, data):
        offset = 16
        flag = struct.unpack("<i", data[offset:offset + 4])[0]
        offset += 4
        full_collection_name, offset = byte2string(data, offset)
        number_to_skip = struct.unpack("<i", data[offset:offset + 4])[0]
        offset += 4
        number_to_return = struct.unpack("<i", data[offset:offset + 4])[0]
        offset += 4
        query, offset = byte2document(data, offset)
        if offset < len(data):
            return_fields_selector, offset = byte2document(data, offset)
        else:
            return_fields_selector = None
        return {
            "flags": flag,
            "fullCollectionName": full_collection_name,
            "numberToSkip": number_to_skip,
            "numberToReturn": number_to_return,
            "query": query,
            "returnFieldsSelector": return_fields_selector
        }

    def do_handle(self, payload: dict, backend) -> dict:
        # query success
        response_flags = 0
        ### ????
        cursor_id = 0
        starting_from = 0
        query_result = []

        full_collection_name = payload["fullCollectionName"]
        db_name, table_name = full_collection_name.split(".")
        collection = getattr(backend, db_name)
        table = getattr(collection, table_name)
        query = payload["query"]
        actual_query = query.get("$query", query)
        order_by = query.get("$orderby", None)

        skip = payload["numberToSkip"]
        limit = payload["numberToReturn"]
        ### ????
        explain = query.get("$explain", None)
        hint = query.get("$hint", None)
        # ignored return fields selector
        try:
            query_result = table.find(filter=actual_query, sort=order_by, limit=limit, skip=skip)
        except Exception as e:
            # query failed
            response_flags = arry2flag([0, 1, 0, 0])
        return {
            "responseFlags": response_flags,
            "cursorID": cursor_id,
            "startingFrom": starting_from,
            "documents": query_result
        }