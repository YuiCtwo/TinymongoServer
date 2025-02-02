from datetime import datetime

from backend.parser import *
from tinymongo import TinyMongoClient
from utils.logger import server_logger

class TinyMongoDBBackend:

    def __init__(self):
        # get an instance of database in tinymongo
        # see example in https://github.com/schapman1974/tinymongo
        self.logger = server_logger
        self.backend = TinyMongoClient()

        self.allowed_commands = {
            OpCode.OP_INSERT: self.handle_insert,
            OpCode.OP_UPDATE: self.handle_update,
            OpCode.OP_DELETE: self.handle_delete,
            OpCode.OP_GET_MORE: self.handle_get_more,
            OpCode.OP_KILL_CURSORS: self.handle_kill_cursors,
            OpCode.OP_QUERY: self.handle_query,
            OpCode.OP_COMPRESSED: self.handle_compressed,
            OpCode.OP_MSG: self.handle_msg,
        }
        self.op_parser_mapping = {
            OpCode.OP_INSERT: InsertParser(),
            OpCode.OP_UPDATE: UpdateParser(),
            OpCode.OP_DELETE: DeleteParser(),
            OpCode.OP_GET_MORE: GetMoreParser(),
            OpCode.OP_KILL_CURSORS: KillCursorsParser(),
            OpCode.OP_QUERY: QueryParser(),
            OpCode.OP_COMPRESSED: CompressedParser(),
            OpCode.OP_MSG: MSGParser(),
        }

    def handle_decode(self, op_code, data):
        # used for testing only
        # decode the data and return the result
        return self.op_parser_mapping[op_code].do_decode(data)


    def handle_insert(self, data):
        payload = self.op_parser_mapping[OpCode.OP_INSERT].do_decode(data)
        self.logger.info(f"Insert Operation: {payload}")
        flags = payload["flags"]

        full_collection_name = payload["fullCollectionName"]
        # collection_name like "db.collection"
        db_name, table_name = full_collection_name.split(".")
        collection = getattr(self.backend, db_name)
        table = getattr(collection, table_name)
        documents = payload["documents"]
        record_id = table.insert_multiple(documents)
        return {}

    def handle_update(self, data):
        payload = self.op_parser_mapping[OpCode.OP_UPDATE].do_decode(data)
        flags = payload["flags"]
        full_collection_name = payload["fullCollectionName"]
        db_name, table_name = full_collection_name.split(".")
        collection = getattr(self.backend, db_name)
        table = getattr(collection, table_name)
        selector = payload["selector"]
        update = payload["update"]
        if flags == 1:
            # update or insert
            if len(self.backend.find(selector)) == 0:
                # insert
                table.insert_one(update)
        elif flags == (1 << 1):
            # It seems that TinyMongo may not support multi-update
            table.update(selector, update, multi=True)
        else:
            table.update(selector, update)
        return {}

    def handle_delete(self, data):
        payload = self.op_parser_mapping[OpCode.OP_DELETE].do_decode(data)
        flag = payload["flags"]
        full_collection_name = payload["fullCollectionName"]
        db_name, table_name = full_collection_name.split(".")
        collection = getattr(self.backend, db_name)
        table = getattr(collection, table_name)
        documents = payload["documents"]
        for document in documents:
            table.remove(document, multi=bool(flag))
        return {}

    def handle_get_more(self, data):
        payload = self.op_parser_mapping[OpCode.OP_GET_MORE].do_decode(data)
        raise NotImplementedError("Don't support GetMore operation yet for TinyMongo backend.")

    def handle_kill_cursors(self, data):
        payload = self.op_parser_mapping[OpCode.OP_KILL_CURSORS].do_decode(data)
        raise NotImplementedError("Don't support KillCursors operation yet for TinyMongo backend.")

    def handle_query(self, data):
        payload = self.op_parser_mapping[OpCode.OP_QUERY].do_decode(data)
        # query success
        response_flags = 0
        ### ????
        cursor_id = 0
        starting_from = 0
        query_result_list = []

        full_collection_name = payload["fullCollectionName"]
        db_name, table_name = full_collection_name.split(".")
        collection = getattr(self.backend, db_name)
        table = getattr(collection, table_name)
        query = payload["query"]
        if query.get("ismaster", False):
            return self.handle_hello(payload)

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

    def handle_compressed(self, data):
        pass

    def handle_msg(self, data):
        pass

    def handle_hello(self, payload):
        # hello-master do not supported for TinyMongo backend
        # so we just return a fake response
        return {
            "responseFlags": 0,
            "cursorID": 0,
            "startingFrom": 0,
            "documents": [{
                'helloOk': True,
                'ismaster': True,
                'maxBsonObjectSize': 16777216,
                'maxMessageSizeBytes': 48000000,
                'maxWriteBatchSize': 100000,
                'logicalSessionTimeoutMinutes': 30,
                'localTime': datetime.now(),
                'connectionId': 8,  # ????
                'minWireVersion': 0,
                'maxWireVersion': 25,
                'readOnly': False,
                'ok': 1.0
            }]
        }