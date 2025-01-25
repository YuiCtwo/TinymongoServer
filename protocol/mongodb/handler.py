import struct
import bson

from utils.logger import server_logger
from protocol.op_code import OpCode

def array2flag(arr):
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

def byte2int32(data, offset):
    """
    Convert byte data to integer.
    :param data: byte data
    :param offset: pointer to the start of the integer
    :return: pointer to the end of the integer and the integer
    """
    integer = struct.unpack("<i", data[offset:offset+4])[0]
    return offset+4, integer

def byte2int64(data, offset):
    """
    Convert byte data to integer.
    :param data: byte data
    :param offset: pointer to the start of the integer
    :return: pointer to the end of the integer and the integer
    """
    integer = struct.unpack("<q", data[offset:offset+8])[0]
    return offset+8, integer

def byte2document(data, offset):
    """
    Covert byte data to dict object in Python
    :param data: byte data
    :param offset: pointer to the start of the document
    :return: offset and decoded document result
    """
    doc_length = struct.unpack("<i", data[offset: offset+4])[0]
    document = bson.decode(data[offset: offset+doc_length])
    offset += doc_length
    return offset, document

class HeadHandler:

    def do_decode(self, data):
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

    def do_decode(self, data):
        """
        :param data: raw data received from client
        :return: json object contains the request payload
        """
        # DO NOT USE THIS METHOD, IT IS JUST A PLACEHOLDER
        return bson.decode(data)

    def do_handle(self, payload: dict, backend) -> dict:
        """
        :param payload: json object contains the request payload
        :param backend: a collection object in TinyMongo
        :return: response payload in json object
        """
        # if no response required, return empty dict
        return {}

    def do_encode(self, payload_dict):
        pass

class InsertHandler(MongoDBHandler):

    def __init__(self):
        super().__init__()
        self.op_code = OpCode.OP_INSERT
        self.supported_version = 5.0

    def do_decode(self, data):
        offset = 16
        offset, flag = byte2int32(data, offset)
        offset, full_collection_name = byte2string(data, offset)
        documents = []
        while offset < len(data):
            offset, document = byte2document(data, offset)
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

    def __init__(self):
        super().__init__()
        self.op_code = OpCode.OP_UPDATE
        self.supported_version = 5.0

    def do_decode(self, data):
        offset = 16
        offset, zero = byte2int32(data, offset)
        offset, full_collection_name = byte2string(data, offset)
        offset, flags = byte2int32(data, offset)
        offset, selector = byte2document(data, offset)
        offset, update = byte2document(data, offset)
        return {
            "flags": flags,
            "fullCollectionName": full_collection_name,
            "selector": selector,
            "update": update,
        }

    def do_handle(self, payload: dict, backend) -> dict:
        flags = payload["flags"]
        full_collection_name = payload["fullCollectionName"]
        db_name, table_name = full_collection_name.split(".")
        collection = getattr(backend, db_name)
        table = getattr(collection, table_name)
        selector = payload["selector"]
        update = payload["update"]
        if flags == 1:
            # update or insert
            if len(backend.find(selector)) == 0:
                # insert
                table.insert_one(update)
        elif flags == (1 << 1):
            # It seems that TinyMongo may not support multi-update
            table.update(selector, update, multi=True)
        else:
            table.update(selector, update)
        return {}

class DeleteHandler(MongoDBHandler):

    def __init__(self):
        super().__init__()
        self.op_code = OpCode.OP_DELETE
        self.supported_version = 5.0

    def do_decode(self, data):
        offset = 16
        # `zero` is reserved for future use
        offset, zero = byte2int32(data, offset)
        offset, full_collection_name = byte2string(data, offset)
        offset, flags = byte2int32(data, offset)
        documents = []
        while offset < len(data):
            offset, document = byte2document(data, offset)
            documents.append(document)
        return {
            "flags": flags,
            "fullCollectionName": full_collection_name,
            "documents": documents
        }

    def do_handle(self, payload: dict, backend) -> dict:
        flag = payload["flags"]
        full_collection_name = payload["fullCollectionName"]
        db_name, table_name = full_collection_name.split(".")
        collection = getattr(backend, db_name)
        table = getattr(collection, table_name)
        documents = payload["documents"]
        for document in documents:
            table.remove(document, multi=bool(flag))
        return {}


class GetMoreHandler(MongoDBHandler):

    def __init__(self):
        super().__init__()
        self.op_code = OpCode.OP_GET_MORE
        self.supported_version = 5.0

    def do_decode(self, data):
        offset = 16
        offset, zero = byte2int32(data, offset)
        offset, full_collection_name = byte2string(data, offset)
        offset, number_to_return = byte2int32(data, offset)
        offset, cursor_id = byte2int64(data, offset)
        return {
            "fullCollectionName": full_collection_name,
            "numberToReturn": number_to_return,
            "cursorID": cursor_id
        }

    def do_handle(self, payload: dict, backend) -> dict:
        raise NotImplementedError("Don't support GetMore operation yet for TinyMongo backend.")

class KillCursorsHandler(MongoDBHandler):

    def __init__(self):
        super().__init__()
        self.op_code = OpCode.OP_KILL_CURSORS
        self.supported_version = 5.0

    def do_decode(self, data):
        offset = 16
        offset, zero = byte2int32(data, offset)
        offset, number_of_cursor_ids = byte2int32(data, offset)
        cursor_ids = []
        for i in range(number_of_cursor_ids):
            offset, cursor_id = byte2int64(data, offset)
            cursor_ids.append(cursor_id)
        return {
            "cursorIDs": cursor_ids,
            "numberOfCursorIDs": number_of_cursor_ids
        }

    def do_handle(self, payload: dict, backend) -> dict:
        raise NotImplementedError("Don't support KillCursors operation yet for TinyMongo backend.")


class QueryHandler(MongoDBHandler):
    def __init__(self):
        super().__init__()
        self.op_code = OpCode.OP_QUERY
        self.supported_version = 5.0

    def do_decode(self, data):
        offset = 16
        offset, flags = byte2int32(data, offset)
        offset, full_collection_name = byte2string(data, offset)
        offset, number_to_skip = byte2int32(data, offset)
        offset, number_to_return = byte2int32(data, offset)
        offset, query = byte2document(data, offset)
        if offset < len(data):
            offset, return_fields_selector = byte2document(data, offset)
        else:
            return_fields_selector = None
        return {
            "flags": flags,
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
        query_result_list = []

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
            query_result_list = [query_result[i] for i in range(query_result.count())]
        except Exception as e:
            # query failed
            response_flags = array2flag([0, 1, 0, 0])
        return {
            "responseFlags": response_flags,
            "cursorID": cursor_id,
            "startingFrom": starting_from,
            "documents": query_result_list
        }

    def do_encode(self, payload_dict):
        query_bson = bson.encode(payload_dict["query"])
        flags_byte = struct.pack("<i", payload_dict["flags"])
        collection_name = payload_dict["fullCollectionName"]
        collection_name_byte = collection_name.encode("utf-8") + b"\x00"
        number_to_skip_byte = struct.pack("<i", payload_dict["numberToSkip"])
        number_to_return_byte = struct.pack("<i", payload_dict["numberToReturn"])

        # 构造完整消息
        message = flags_byte + collection_name_byte + number_to_skip_byte + number_to_return_byte + query_bson
        return message

class CompressedHandler(MongoDBHandler):
    pass

class MSGHandler(MongoDBHandler):
    pass

class ReplyHandler(MongoDBHandler):

    def do_decode(self, data):
        offset = 16
        flags, cursor_id, starting_from, number_returned = struct.unpack('<iqii', data[offset:offset+20])
        documents = []
        offset += 20
        for i in range(number_returned):
            offset, document = byte2document(data, offset)
            documents.append(document)
        return {
            'flags': flags,
            'cursorID': cursor_id,
            'startingFrom': starting_from,
            'numberReturned': number_returned,
            'documents': documents
        }