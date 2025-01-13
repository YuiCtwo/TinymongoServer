import struct
import bson

def payload2response(response_to, request_id, response_json):
    response_payload = bson.dumps(response_json)

    message_length = len(response_payload) + 16

    # little endian, 4 int32
    # OP_REPLY = 1
    response_header = struct.pack("<iiii", message_length, request_id, response_to, 1)

    return response_header + response_payload

def payload2compressed_response(response_to, request_id, response_json):
    # used for version 5.1+
    pass