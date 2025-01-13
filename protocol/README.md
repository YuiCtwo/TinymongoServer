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

## 参考
- [MongoDB Wire Protocol](https://www.mongodb.com/zh-cn/docs/manual/reference/mongodb-wire-protocol/)