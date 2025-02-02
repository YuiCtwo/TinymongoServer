import struct
from typing import List

import bson


from backend.op_code import OpCode
from utils.http_utils import crc32_checksum
from utils.logger import server_logger


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

def flag2array(flag):
    """
    Convert integer to byte like `00011000` stored in array.
    :param flag: unsigned integer
    :return: length<=32, every element is 0 or 1 represents a bit.
    """
    arr = [0] * 32
    for idx in range(32):
        arr[idx] = (flag >> idx) & 1
    return arr

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

def byte2uint32(data, offset):
    """
    Convert byte data to unsigned integer.
    :param data: byte data
    :param offset: pointer to the start of the integer
    :return: pointer to the end of the integer and the integer
    """
    integer = struct.unpack("<I", data[offset:offset+4])[0]
    return offset+4, integer

def byte2sections(data, offset):
    current_offset = offset
    current_offset, section_size = byte2int32(data, current_offset)
    section_name = byte2string(data, current_offset)
    documents = []
    while current_offset < offset + section_size:
        current_offset, document = byte2document(data, current_offset)
        documents.append(document)
    res = {
        section_name: documents
    }
    return current_offset, res

class HeadParser:

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


class MongoDBParser:
    def __init__(self):

        self.op_code = OpCode.OP_DUMMY
        self.supported_version = 0.0

    def do_decode(self, data) -> dict:
        """
        :param data: raw data received from client
        :return: json object contains the request payload
        """
        # DO NOT USE THIS METHOD, IT IS JUST A PLACEHOLDER
        return {}

    def do_encode(self, payload_dict):
        return None

class InsertParser(MongoDBParser):

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


class UpdateParser(MongoDBParser):

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
            "responseFlags": flags,
            "fullCollectionName": full_collection_name,
            "selector": selector,
            "update": update,
        }


class DeleteParser(MongoDBParser):

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


class GetMoreParser(MongoDBParser):

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

class KillCursorsParser(MongoDBParser):

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


class QueryParser(MongoDBParser):
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

    def do_encode(self, payload_dict):
        query_bson = bson.encode(payload_dict["query"])
        flags_byte = struct.pack("<i", payload_dict["flags"])
        collection_name = payload_dict["fullCollectionName"]
        collection_name_byte = collection_name.encode("utf-8") + b"\x00"
        number_to_skip_byte = struct.pack("<i", payload_dict["numberToSkip"])
        number_to_return_byte = struct.pack("<i", payload_dict["numberToReturn"])

        # construct the complete message
        message = flags_byte + collection_name_byte + number_to_skip_byte + number_to_return_byte + query_bson
        return message

class CompressedParser(MongoDBParser):
    pass

class MSGParser(MongoDBParser):

    def __init__(self):
        super().__init__()
        self.op_code = OpCode.OP_MSG
        self.supported_version = 8.0

    def do_decode(self, data):
        offset = 16
        offset, flag_bits = byte2int32(data, offset)
        message_length = len(data)
        if flag_bits & 0x01:
            message_length -= 4
            # The message ends with 4 bytes containing a CRC-32C
            checksum = struct.unpack("<i", data[message_length:message_length+4])[0]
            # compute all data include head
            print(f"CRC-32C checksum: {checksum}")
            if not crc32_checksum(data[:-4], checksum):
                server_logger.warning("CRC-32C checksum failed, discard the message.")
                return {}
        with open("hello_next.bin", "wb") as f:
            f.write(data[16:])
        sections = []
        while offset < len(data):
            # one 8-bit number represents one kind of section
            kind = struct.unpack("<b", data[offset:offset+1])[0]
            offset += 1
            if kind == 0:
                # Type 0: single document section
                offset, document = byte2document(data, offset)
                sections.append(document)
            elif kind == 1:
                # Type 1: document sequence section
                offset, section = byte2sections(data, offset)
                sections.append(section)
            elif kind == 2:
                # This section is used for internal purposes.
                pass
            else:
                server_logger.warning("Unknown section type: {}".format(kind))
        return {
            "flagBits": flag_bits,
            "sections": sections
        }

    def do_encode(self, payload_dict):
        message_body = b''
        for section in payload_dict["sections"]:
            document_type = 0
            kind = struct.pack("<b", document_type)
            message_body += kind
            section_bson = bson.encode(section)
            message_body += section_bson

        flags_byte = struct.pack("<i", payload_dict["flagBits"])

        # construct the complete message
        message = flags_byte + message_body
        return message



class ReplyParser(MongoDBParser):

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