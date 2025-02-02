# MongoDB Wire Protocol

我们要做的是实现一个 Fake MongoDB Server， 它可以接受来自客户端的请求，由我们模拟服务端的处理，交付给实际的存储引擎（TinyMongoDB）。
然后返回响应给客户端。

MongoDB 使用的是基于 TCP/IP 的套接字连接与服务器通信，通信使用简单的请求-响应套接字协议，
即客户机向服务器发送请求，而服务器则对请求作出响应。

请求应包括**消息头**和**请求有效负载**，而响应则包括**消息头**和**响应有效负载**
- 需要注意：
    - 请求和响应的有效负载并不相同
    - 消息头和有效负载都是 BSON 格式的二进制数据
    - 消息的排序遵循小端序（little-endian）

基于 MongoDB 官方文档较差的可读性，这里参考现有实现，整理出 MongoDB 通信协议的实现细节。

## BSON

BSON（Binary JSON）是一种二进制形式的 JSON 文档。它是 MongoDB 数据库的默认数据存储格式。

## 消息头

```c
struct MsgHeader {
    int32   messageLength; // total message size, including this
    int32   requestID;     // identifier for this message
    int32   responseTo;    // requestID from the original request
                           //  (used in responses from the database)
    int32   opCode;        // message type
}
```
- messageLength：整个消息的大小，包括消息头
- requestID：每个请求的唯一标识符，由客户端或数据库生成
- responseTo：如果是响应，则为请求的 requestID；如果是请求，则为 0
- opCode：消息类型，包括请求、响应、错误、通知等

## 请求有效负载

不同的请求类型，其有效负载格式也不同。（甚至不同版本也不太一样）
从 5.1 版本开始，OP_MSG 和 OP_COMPRESSED 是向 Server 发送请求时唯一支持的操作码

### OP_COMPRESSED
5.1 版本的压缩请求，用于支持压缩数据。

### OP_MSG
5.1 版本的消息请求，用于支持多文档事务。

### OP_INSERT

### OP_UPDATE

### OP_DELETE

### OP_GET_MORE

### OP_KILL_CURSORS

### OP_QUERY

### OP_REPLY

### OP_UPDATE

## BSON Document & Collection

文档是 MongoDB 的基本数据单元，使用 BSON 格式存储。一个文档包含了一组键值对，类似于 JSON 对象。
如： `{"name": "John", "age": 30, "city": "New York"}`

而集合（Collection）则是文档的一个集合，类似于关系型数据库中的表（Table）。每个集合可以包含多个文档，而集合本身不需要预定义其结构。

## 参考
- [MongoDB Wire Protocol](https://www.mongodb.com/zh-cn/docs/manual/reference/mongodb-wire-protocol/)

# Connect to Client

选择 MongoDB Compass 作为客户端（版本 > 5.1），连接到我们实现的 Fake MongoDB Server。
连接刚开始的时候会不断地尝试发送 OP_QUERY 请求
请求内容为：
```txt
{
    "flags": 0,
    "fullCollectionName": "admin.$cmd",
    "numberToSkip": 0,
    "numberToReturn": -1,
    "query": {
        "ismaster": 1,
        "helloOk": True,
        "client": {
            "application": {
                "name": "MongoDB Compass"
            },
            "driver": {
                "name": "nodejs",
                "version": "6.12.0"
            },
            "platform": "Node.js v20.18.1, LE",
            "os": {
                "name": "win32",
                "architecture": "x64",
                "version": "10.0.22631",
                "type": "Windows_NT"
            }
        },
        "compression": ["none"]
    },
    "returnFieldsSelector": None
}
```
> MongoDB 5.1 已删除对 OP_QUERY 查找操作和 OP_QUERY 命令的支持。但有一例外：运行 hello 和 isMaster 命令以作为连接握手的一部分仍然支持 OP_QUERY。

详细的 hello 命令可以参考官方文档 https://www.mongodb.com/zh-cn/docs/manual/reference/command/hello/#mongodb-dbcommand-dbcmd.hello



经过测试 返回的响应类似下面的内容：
```txt
{
	'responseFlags': 8,
	'cursorID': 0,
	'startingFrom': 0,
	'numberReturned': 1,
	'documents': [{
		'helloOk': True,
		'ismaster': True,
		'topologyVersion': {
			'processId': ObjectId('67949a0bb94f9cc9296f4d54'),
			'counter': 0
		},
		'maxBsonObjectSize': 16777216,
		'maxMessageSizeBytes': 48000000,
		'maxWriteBatchSize': 100000,
		'localTime': datetime.datetime(2025, 1, 25, 9, 4, 12, 424000),
		'logicalSessionTimeoutMinutes': 30,
		'connectionId': 8,
		'minWireVersion': 0,
		'maxWireVersion': 25,
		'readOnly': False,
		'ok': 1.0
	}]
```
很可惜，好像目前的个人实现的 MongoDB 单文件数据库基本都不支持 hello 命令，需要我们自己构造虚拟的返回结果。
少了个压缩字段，跟据官方文档的说明，看来 Compass 客户端默认不启用压缩算法，神奇。
> 如果客户端未指定压缩，或者客户端指定了未为连接的 mongod 或 mongos 实例启用的压缩算法，则不会返回该字段。

- localTime 跟据文档说明返回的是服务器的本地 UTC 时间，需要用 datetime 模块获取一下： `datetime.now()`
- topologyVersion 仅供 MongoDB 内部使用，可以忽略，但保险起见还是返回一下。 `ObjectId` 是 MongoDB 的特殊字段，用于标识数据库里面的 `_id`
可以直接调用 bson 库来生成。

对于最新版的 Compass 来说，hello 一旦建立连接成功，会立刻发送一个 OP_MSG 请求，内容为