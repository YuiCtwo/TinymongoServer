import socket

from tinymongo import TinyMongoClient

from protocol.mongodb.handler import *
from utils.http_utils import payload2response, payload2compressed_response
from utils.logger import server_logger

class TinyMongoServer:

    def __init__(self, host='127.0.0.1', port=27017):
        self.host = host
        self.port = port
        # get an instance of database in tinymongo
        # see example in https://github.com/schapman1974/tinymongo
        connection = TinyMongoClient()
        self.backend = connection
        #
        self.logger = server_logger
        self.head_handler = HeadHandler()
        # demo list that stores allowed commands
        self.allowed_commands = {
            OpCode.OP_INSERT: InsertHandler(),
        }

        self._build_socket()
        self.response_parse = payload2response
        self.version = 5.0

    def _build_socket(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        # set maximum number of connections
        self.server_socket.listen(5)
        # log server start
        self.logger.info(f"Server started on {self.host}:{self.port}")

    def start_server(self):
        while True:
            client_socket, client_address = self.server_socket.accept()
            self._handle_request(client_socket)

    def _handle_request(self, client_socket):
        try:
            data = client_socket.recv(1024)
            header = self.head_handler.do_parse(data)
            op_code = header["op_code"]
            # TODO: do we need to generate request_id by ourselves?
            request_id = header["request_id"]
            response_to = header["response_to"]
            if op_code in self.allowed_commands:
                handler = self.allowed_commands[op_code]
                payload = handler.do_parse(data)
                response = handler.do_handle(payload, self.backend)
            else:
                response = {}
            # some of the command may not need to return any response
            if len(response.keys()) != 0:
                response_raw = self.response_parse(response_to, request_id, response)
                client_socket.send(response_raw)

        except ConnectionResetError:
            self.logger.info(f"IP {self.server_socket.getpeername()[0]} disconnected")
        finally:
            client_socket.close()

    def __del__(self):
        self.server_socket.close()


class TinyMongoServer51(TinyMongoServer):
    def __init__(self, host='127.0.0.1', port=27017):
        super().__init__(host, port)
        self.version = 5.1
        self.response_parse = payload2compressed_response
