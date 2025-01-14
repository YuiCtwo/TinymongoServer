import struct
import bson

from utils.logger import server_logger
from protocol.mongodb.op_code import OpCode


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
    :return: decoded document result
    """
    document_list = []
    while offset < len(data):
        doc_length = struct.unpack("<i", data[offset: offset+4])[0]
        document = bson.loads(data[offset: offset+doc_length])
        document_list.append(document)
        offset += doc_length
    return offset, document_list

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
        documents, _ = byte2document(data, offset)
        return {
            "flags": flag,
            "fullCollectionName": full_collection_name,
            "documents": documents
        }


    def do_handle(self, payload: dict, backend) -> dict:
        self.logger.info(f"Insert Operation: {payload}")
        flags = payload["flags"]
        
        full_collection_name = payload["fullCollectionName"]
        documents = payload["documents"]
        # TODO: how to handle error if collection not exist?
        collection = getattr(backend, full_collection_name)
        record_id = collection.insert_multiple(documents)
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
    pass

class ReplyHandler(MongoDBHandler):
    pass