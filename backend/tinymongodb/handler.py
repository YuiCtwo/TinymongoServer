import sys
import time

from datetime import datetime, timezone
from bson import ObjectId

from backend.parser import *
from backend.server_env import get_base_env, get_build_info, get_host_info
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
            # OpCode.OP_GET_MORE: self.handle_get_more,
            # OpCode.OP_KILL_CURSORS: self.handle_kill_cursors,
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
        self.connection_id = 1
        self.object_id = ObjectId()
        # fill up fundamental data in the database
        self.server_database_setup()

    def server_database_setup(self):
        # create a database named "admin", "config", "local"
        required_databases = [
            "admin.$cmd.aggregate",
            "admin.atlascli",
            "admin.system.version",
            "config.system.sessions",
            "config.transactions",
            "local.startup_log",
            "local.system.replset",
        ]
        for db_str in required_databases:
            database_strs = db_str.split(".")
            if len(database_strs) != 2:
                # TODO: understand these confusing structure of database
                continue
            else:
                collection_name, table_name = database_strs
                # the database will be created automatically when we access it if it doesn't exist
                collection = getattr(self.backend, collection_name)
                table = getattr(collection, table_name)



    def handle_decode(self, op_code, data):
        # used for testing only
        # decode the data and return the result
        return self.op_parser_mapping[op_code].do_decode(data)

    def handle_insert(self, data):
        payload = self.op_parser_mapping[OpCode.OP_INSERT].do_decode(data)
        self.logger.info(f"Insert Operation: {payload}")
        flags = payload["responseFlags"]

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
        flags = payload["responseFlags"]
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
        flag = payload["responseFlags"]
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

        if "ismaster" in query and query["ismaster"] == 1:
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
        payload = self.op_parser_mapping[OpCode.OP_MSG].do_decode(data)
        print(payload)
        return_flags = 0
        if "flagBits" in payload:
            is_checksumPresent = payload["flagBits"] & 1
            is_moreToCome = (payload["flagBits"] >> 1) & 1
            is_exhaustAllowed = (payload["flagBits"] >> 16) & 1
            if is_checksumPresent:
                return_flags += 1
            if is_exhaustAllowed:
                return_flags += (1 << 1)
            if is_moreToCome:
                # more to come, return None
                return {}
            else:
                sections = payload["sections"]
                sections0 = sections[0]
                # no more to come, handle the payload
                # handle admin & hello command
                if "hello" in sections0 and sections0["hello"] == 1:
                    return_sections = self.handle_msg_hello(payload)
                elif "ping" in sections0 and sections0["ping"] == 1:
                    return_sections = [{"ok": 1.0}]
                elif "top" in sections0 and sections0["top"] == 1:
                    return_sections = self.handle_top(payload)
                elif "buildInfo" in sections0 and sections0["buildInfo"] == 1:
                    return_sections = self.handle_buildInfo(payload)
                elif "hostInfo" in sections0 and sections0["hostInfo"] == 1:
                    return_sections = self.handle_hostInfo(payload)
                else:
                    return_sections = [{"ok": 1.0}]

                return {
                    "flagBits": return_flags,
                    "sections": return_sections
                }
        else:
            self.logger.warning("Skipping payload without flagBits.")
            return {}

    def handle_msg_hello(self, payload):
        base_env_info = get_base_env()

        base_env_info['isWritablePrimary'] = True
        base_env_info['topologyVersion'] = {
            'processId': self.object_id,
            'counter': bson.int64.Int64(0)
        }
        base_env_info['connectionId'] = self.connection_id
        base_env_info['ok'] = 1.0

        return [base_env_info]

    def handle_hello(self, payload):
        # hello-master do not support for TinyMongo backend
        # so we just return a fake response
        base_env_info = get_base_env()
        base_env_info['topologyVersion'] = {
            'processId': self.object_id,
            'counter': bson.int64.Int64(0)
        }
        base_env_info['connectionId'] = self.connection_id
        base_env_info['ok'] = 1.0
        base_env_info['helloOk'] = True
        base_env_info['ismaster'] = True
        return {
            "responseFlags": 8,
            "cursorID": 0,
            "startingFrom": 0,
            'numberReturned': 1,
            "documents": [base_env_info]
        }

    def handle_buildInfo(self, payload):
        build_info = get_build_info()
        build_info['ok'] = 1.0
        return [build_info]

    def handle_hostInfo(self, payload):
        host_info = get_host_info()
        host_info['ok'] = 1.0
        return [host_info]

    def handle_top(self, payload):
        databases = self.backend.list_database_names()
        return [{}]