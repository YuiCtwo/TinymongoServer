import random
import sys
import time

from datetime import datetime, timezone
from bson import ObjectId

from backend.op_code import get_code_name, ErrorCode
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
            "admin.database",
            "config.system",  # configuration parameters
            "local.startup_log"  # logs
        ]
        for db_str in required_databases:
            database_strs = db_str.split(".")
            collection_name, table_name = database_strs
            # the database will be created automatically when we access it if it doesn't exist
            collection = getattr(self.backend, collection_name)
            table = getattr(collection, table_name)
            table.find()
        admin_table = self.backend.admin.database
        # ignore admin as it is an `inner` database controlled by program
        admin_table.insert_many([
            {"name": "config"},
            {"name": "local"}
        ])

    def _get_all_databases(self):
        admin_table = self.backend.admin.database
        query_result = admin_table.find()
        all_databases = [db_doc["name"] for db_doc in query_result]
        return all_databases

    def _get_db_stats(self, database_name):
        # calculate the stats of a specific database
        db = getattr(self.backend, database_name)
        collection_names = db.collection_names()
        # TODO: implementations
        return {
            "db": database_name,
            "collections": len(collection_names),
            "objects": 1,
            "avgObjSize": 59.0,
            "dataSize": 59.0,
            "storageSize": 20480.0,
            "indexes": 1,
            "indexSize": 20480.0,
            "totalSize": 40960.0,
            "scaleFactor": 1,
            "fsUsedSize": 160507240448.0,
            "fsTotalSize": 858992406528.0
        }

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
        return_flags = 0
        self.logger.info(f"Received MSG payload:{payload}")
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
                if sections0.get("hello", None) == 1:
                    return_sections = self.handle_msg_hello(payload)
                elif sections0.get("ping", None) == 1:
                    return_sections = [{"ok": 1.0}]
                elif sections0.get("top", None) == 1:
                    return_sections = self.handle_top(payload)
                elif sections0.get("buildInfo", None) == 1:
                    return_sections = self.handle_buildInfo(payload)
                elif sections0.get("hostInfo", None) == 1:
                    return_sections = self.handle_hostInfo(payload)
                elif sections0.get("atlasVersion", None) == 1:
                    return_sections = self.handle_error("no such command: 'atlasVersion'", 59)
                elif sections0.get("connectionStatus", None) == 1:
                    return_sections = self.handle_authInfo(payload)
                else:
                    return_sections = self.handle_error("Unknown", 0)

                return {
                    "flagBits": return_flags,
                    "sections": return_sections
                }
        else:
            self.logger.warning("Skipping payload without flagBits.")
            return {}

    def handle_msg_hello(self, payload):
        base_env_info = get_base_env()

        base_env_info["isWritablePrimary"] = True
        base_env_info["topologyVersion"] = {
            "processId": self.object_id,
            "counter": bson.int64.Int64(0)
        }
        base_env_info["connectionId"] = self.connection_id
        base_env_info["ok"] = 1.0

        return [base_env_info]

    def handle_hello(self, payload):
        # hello-master do not support for TinyMongo backend
        # so we just return a fake response
        base_env_info = get_base_env()
        base_env_info["topologyVersion"] = {
            "processId": self.object_id,
            "counter": bson.int64.Int64(0)
        }
        base_env_info["connectionId"] = self.connection_id
        base_env_info["ok"] = 1.0
        base_env_info["helloOk"] = True
        base_env_info["ismaster"] = True
        return {
            "responseFlags": 8,
            "cursorID": 0,
            "startingFrom": 0,
            "numberReturned": 1,
            "documents": [base_env_info]
        }

    def handle_buildInfo(self, payload):
        build_info = get_build_info()
        build_info["ok"] = 1.0
        return [build_info]

    def handle_hostInfo(self, payload):
        host_info = get_host_info()
        host_info["ok"] = 1.0
        return [host_info]

    def handle_top(self, payload):
        databases = self._get_all_databases()
        return_sections = {
            "totals": {
                "note": "all times in microseconds",
            }
        }
        for db_name in databases:
            collection = getattr(self.backend, db_name)
            for table_name in collection.list_collection_names():
                table = getattr(collection, table_name)
                # TODO: do something for time testing
                result_key = f"{db_name}.{table_name}"
                result_value = {}
                for op_name in ["queries", "getmore", "insert", "update", "remove", "commands"]:
                    result_value[op_name] = {
                        "time": 0,
                        "count": 0
                    }
                result_value["readLock"] = {
                    "time": random.randint(800, 1200),
                    "count": random.randint(10, 100)
                }
                result_value["writeLock"] = {
                    "time": random.randint(800, 1200),
                    "count": random.randint(10, 100)
                }
                result_value["total"] = {
                    "time": result_value["writeLock"]["time"] + result_value["readLock"]["time"],
                    "count": result_value["writeLock"]["count"] + result_value["readLock"]["count"]
                }
                return_sections["totals"][result_key] = result_value
        return_sections["ok"] = 1.0
        return [return_sections]

    def handle_error(self, err_msg, err_code:int):
        return_sections = {
            "ok": 0.0,
            "errmsg": err_msg,
            "code": err_code,
            "codeName": get_code_name(ErrorCode, err_code)
        }
        return [return_sections]

    def handle_getParameter(self, payload):
        return [{
            "ok": 1.0,
            "featureCompatibilityVersion": {"version": "8.0"}
        }]

    def handle_listDatabases(self, payload):
        all_databases = self._get_all_databases()
        return [{
            "ok": 1.0,
            "databases": [
                {"name": db_name} for db_name in all_databases
            ]
        }]

    def handle_dbStats(self, payload):
        return_section = self._get_db_stats("admin")
        return_section["ok"] = 1.0
        return [return_section]

    def handle_authInfo(self, payload):
        # still confusing
        return [{
            "authInfo": {
                "authenticatedUsers": [],
                "authenticatedUserRoles": [],
                "authenticatedUserPrivileges": []
            },
            "ok": 1.0
        }]
