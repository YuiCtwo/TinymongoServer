import struct
import bson
import zlib


def crc32_checksum(raw_data, checksum):
    """
    Calculate the CRC32 checksum of the given data and compare it with the given checksum.
    :param raw_data: Total data except the checksum
    :param checksum: The expected checksum
    :return:
    """
    computed_checksum = zlib.crc32(raw_data) & 0xFFFFFFFF
    return computed_checksum == checksum

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
    response_header = struct.pack("<iiii", message_length, request_id, response_to, 1)
    response_body = struct.pack("<iqii", flags, cursor_id, starting_from, number_documents)

    return response_header + response_body + response_payload

def payload2compressed_response(response_to, request_id, response_json):
    # used for version 5.1+
    pass