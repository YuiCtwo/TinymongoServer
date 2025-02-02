# basic code for MongoDB OpCode in protocol

class OpCode:
    OP_DUMMY = 0
    OP_COMPRESSED = 2012
    OP_MSG = 2013
    # allow used in MongoDB <= 5.0
    OP_REPLY = 1
    OP_UPDATE = 2001
    OP_INSERT = 2002
    RESERVED = 2003
    OP_QUERY = 2004
    OP_GET_MORE = 2005
    OP_DELETE = 2006
    OP_KILL_CURSORS = 2007