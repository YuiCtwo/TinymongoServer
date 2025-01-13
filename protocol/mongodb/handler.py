from utils.logger import server_logger
from protocol.mongodb.op_code import OpCode

class HeadHandler:
    def __init__(self):
        pass

    def do_parse(self, data):
        pass

class MongoDBHandler:
    def __init__(self):
        self.logger = server_logger
        self.op_code = OpCode.OP_DUMMY
        self.supported_version = 0.0

    def do_parse(self, data):
        pass

    def do_handle(self, payload, backend):
        pass

class CompressedHandler(MongoDBHandler):
    pass

class MSGHandler(MongoDBHandler):
    pass

class InsertHandler(MongoDBHandler):
    pass

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