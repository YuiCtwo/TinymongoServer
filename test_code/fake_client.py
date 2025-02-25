import socket
import struct
import time
import threading

from backend.op_code import OpCode
from backend.parser import HeadParser, QueryParser, ReplyParser, MSGParser


def read_binary_request(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
    return data

class MongoDBClient:
    def __init__(self, host='127.0.0.1', port=27017):
        self.client_socket = None
        self.host = host
        self.port = port
        self.request_id = 0
        self.query_handler = QueryParser()
        self.head_handler = HeadParser()
        self.reply_handler = ReplyParser()
        self.msg_handler = MSGParser()
        self.connect()

    def connect(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))
        print(f"Connected to MongoDB server at {self.host}:{self.port}")

    def close(self):
        self.client_socket.close()
        print("Connection closed")

    def send_message(self, op_code, message):
        # 构造消息头
        message_length = 16 + len(message)  # 消息头长度 + 消息体长度
        request_id = self.request_id
        response_to = 0
        header = struct.pack('<iiii', message_length, request_id, response_to, op_code)

        # 发送消息
        self.client_socket.send(header + message)
        self.request_id += 1

    # def recv_header(self):
    #     header_raw = self.client_socket.recv(16)
    #     if len(header_raw) < 16:
    #         raise Exception("Invalid response header")
    #     message_length, request_id, response_to, op_code = struct.unpack('<iiii', header_raw)
    #     return message_length, request_id, response_to, op_code
    #
    # def recv_body(self, body_length):
    #     body_raw = self.client_socket.recv(body_length)
    #     if len(body_raw) < body_length:
    #         raise Exception("Invalid response body")
    #     return body_raw

    def request_hello(self):
        from json_request.hello import payload
        msg = self.query_handler.do_encode(payload)
        self.send_message(OpCode.OP_QUERY, msg)
        print("Sent `hello` request to MongoDB server")
        response_raw = self.client_socket.recv(1024)
        header = self.head_handler.do_decode(response_raw)
        result = self.reply_handler.do_decode(response_raw)
        result["response_length"] = header["message_length"]
        result["request_id"] = header["request_id"]
        result["response_to"] = header["response_to"]
        result["op_code"] = header["op_code"]
        print(result)

    def request_hello_msg(self):
        # binary_file = "json_request/hello_next.bin"
        # msg = read_binary_request(binary_file)
        from json_request.hello_next import payload
        msg = self.msg_handler.do_encode(payload)
        self.send_message(OpCode.OP_MSG, msg)
        print("Sent `MSG` request to MongoDB server")
        response_raw = self.client_socket.recv(4096)
        header = self.head_handler.do_decode(response_raw)
        result = self.msg_handler.do_decode(response_raw)
        result["response_length"] = header["message_length"]
        result["request_id"] = header["request_id"]
        result["response_to"] = header["response_to"]
        result["op_code"] = header["op_code"]
        print(result)

    def request_admin_command(self):
        from json_request.admin_command import payload_agg
        msg = self.msg_handler.do_encode(payload_agg)
        self.send_message(OpCode.OP_MSG, msg)
        print("Sent `agg` request to MongoDB server")
        response_raw = self.client_socket.recv(4096)
        result = self.msg_handler.do_decode(response_raw)
        print(result)

    def request_buildInfo(self):
        from json_request.admin_command import payload_buildInfo
        msg = self.msg_handler.do_encode(payload_buildInfo)
        self.send_message(OpCode.OP_MSG, msg)
        print("Sent `buildInfo` request to MongoDB server")
        response_raw = self.client_socket.recv(4096)
        result = self.msg_handler.do_decode(response_raw)
        print(result)

    def request_top(self):
        from json_request.admin_command import payload_top
        msg = self.msg_handler.do_encode(payload_top)
        self.send_message(OpCode.OP_MSG, msg)
        print("Sent `top` request to MongoDB server")
        response_raw = self.client_socket.recv(4096)
        result = self.msg_handler.do_decode(response_raw)
        print(result)

    def request_hostInfo(self):
        from json_request.admin_command import payload_hostInfo
        msg = self.msg_handler.do_encode(payload_hostInfo)
        self.send_message(OpCode.OP_MSG, msg)
        print("Sent `hostInfo` request to MongoDB server")
        response_raw = self.client_socket.recv(4096)
        result = self.msg_handler.do_decode(response_raw)
        print(result)

    def request_any_info(self, payload):
        msg = self.msg_handler.do_encode(payload)
        self.send_message(OpCode.OP_MSG, msg)
        print("Sent `Info` request to MongoDB server")
        response_raw = self.client_socket.recv(4096)
        result = self.msg_handler.do_decode(response_raw)
        print(result)

def thread_function1():
    client = MongoDBClient(host='127.0.0.1', port=27017)
    client.request_hello()
    client.request_hello_msg()
    client.close()

def thread_function2():
    client = MongoDBClient(host='127.0.0.1', port=27017)
    # client.request_admin_command()
    # client.request_buildInfo()
    # client.request_top()
    # client.request_hostInfo()
    import json_request.admin_command as command
    client.request_any_info(command.payload_atlasVersion)
    client.request_any_info(command.payload_getParameter)
    client.request_any_info(command.payload_listDatabases)
    client.request_any_info(command.payload_dbStats)
    client.request_any_info(command.payload_authInfo)
    client.close()

if __name__ == "__main__":
    thread1 = threading.Thread(target=thread_function1)
    thread2 = threading.Thread(target=thread_function2)
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
    # while True:
    #     data = client.client_socket.recv(1024)
    #     header = client.head_handler.do_decode(data)
    #     msg = client.msg_handler.do_decode(data)
    #     print(header)
    #     print(msg)
        # print(time.time() - response_start)