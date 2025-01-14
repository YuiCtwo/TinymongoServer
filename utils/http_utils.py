import struct
import bson

from protocol.mongodb.op_code import OpCode


def payload2response(response_to, request_id, response_json):
    """
    Convert a response payload to a binary message.
    According to the MongoDB Wire Protocol, the response message is a `OP_REPLY` message
    :param response_to: reqeust_id of the original request
    :param request_id: identifier for this response
    :param response_json: json data to reply
    :return: binary string
    """
    response_payload = bson.dumps(response_json)

    message_length = len(response_payload) + 16

    # little endian, 4 int32
    response_header = struct.pack("<iiii", message_length, request_id, response_to, 1)

    return response_header + response_payload

def payload2compressed_response(response_to, request_id, response_json):
    # used for version 5.1+
    pass