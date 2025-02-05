import struct
import bson

from backend.parser import MSGParser
from backend.op_code import OpCode


def payload2response(response_to, request_id, response_json):
    """
    Convert a response payload to a binary message. USED FOR VERSION < 5.0
    According to the MongoDB Wire Protocol, the response message is a `OP_REPLY` message
    :param response_to: reqeust_id of the original request
    :param request_id: identifier for this response
    :param response_json: json data to reply
    :return: binary string
    """
    number_documents = len(response_json["documents"])
    flags = response_json["responseFlags"]
    cursor_id = response_json["cursorID"]
    starting_from = response_json["startingFrom"]
    response_payload = b"".join(bson.encode(doc) for doc in response_json["documents"])

    # header: 16, response_header: 20, documents: len(response_payload)
    message_length = len(response_payload) + 16 + 20

    # little endian, 4 int32
    response_header = struct.pack("<iiii", message_length, request_id, response_to, OpCode.OP_REPLY)
    response_body = struct.pack("<iqii", flags, cursor_id, starting_from, number_documents)
    return response_header + response_body + response_payload

def payload2compressed_response(response_to, request_id, response_json):
    # used for version 5.1+
    pass


def payload2msg_response(response_to, request_id, response_json):
    parser = MSGParser()
    msg = parser.do_encode(response_json)
    message_length = len(msg) + 16
    response_header = struct.pack("<iiii", message_length, request_id, response_to, OpCode.OP_MSG)
    return response_header + msg