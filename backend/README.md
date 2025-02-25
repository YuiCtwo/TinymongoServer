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

```text
OP_MSG {
    MsgHeader header;           // standard message header
    uint32 flagBits;            // message flags
    Sections[] sections;        // data sections
    optional<uint32> checksum;  // optional CRC-32C checksum
}
```
比较关键的部分在于：flagBits 标志位和 sections 消息数组：
- flagBits: 前 16 位必须有，我个人的理解是只能设置有实际含义的二进制位，否则，解析器则必须报错。
原文是 `"The first 16 bits (0-15) are required and parsers MUST error if an unknown bit is set."`
最后 16 位是可选的，允许设置一些额外的标志位，但代理和其他消息转发器必须在转发消息之前清除任何未知的可选位。

必须要吐槽的是，因为数据类型是 uint32，所以必然有 32 位啊！
并且实际情况下 Compass 客户端发出的请求中 flagBits 前 15 位没有含义的位都被设置为了 1。

旧版本的操作码不再列出，详细的可以查看官方文档。

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

```text
    'flagBits': 65536,
    'sections': [{
        'hello': 1,
        'maxAwaitTimeMS': 10000,
        'topologyVersion': {
            'processId': ObjectId('679f5fe50ab84b41447995a7'),
            'counter': 0
        },
        '$db': 'admin'
    }]
```
依旧看不明白，果断发给官方的 Server 拿返回结果，值得一提的是 'topologyVersion' 的 'counter' 类型是 Long，不好使用 Python 指定他的类型，
所以直接存一个二进制文件用于测试比较合适。 

```text
{
	'flagBits': 2,
	'sections': [{
		'isWritablePrimary': True,
		'topologyVersion': {
			'processId': ObjectId('679f372744513c4d2d152cb0'),
			'counter': 0
		},
		'maxBsonObjectSize': 16777216,
		'maxMessageSizeBytes': 48000000,
		'maxWriteBatchSize': 100000,
		'localTime': datetime.datetime(2025, 2, 2, 12, 52, 51, 653000),
		'logicalSessionTimeoutMinutes': 30,
		'connectionId': 17,
		'minWireVersion': 0,
		'maxWireVersion': 25,
		'readOnly': False,
		'ok': 1.0
	}],
	'response_length': 313,
	'request_id': 919,
	'response_to': 1,
	'op_code': 2013
}
```

看样子是 MSG 版本的 hello 命令，注意 flagBits 变为 2
> 仅当响应已设置 exhaustAllowed 位的请求时，回复才会设置此位。

因为我们在请求的时候设置了 exhaustAllowed 位，所以返回的响应中才会在第一个位上有 1。
顺便一提如果请求出现错误，那么返回的 flagBits 应该全部设置为 0。

接着会发送另外一个 OP_MSG：
```text
{'flagBits': 0, 'sections': [{'ping': 1, 'lsid': {'id': Binary(b'\xad\x98\xeb\xe2\xa1\xf5G\xef\xbd\xcc\xde\x01H\xaeA\xa9', 4)}, '$db': 'admin'}]}
```
跟据官方文档：
> ping 命令是一个空操作，用于测试服务器是否在响应命令。即使服务器处于写锁定状态，此命令也会立即返回：
> lsid 指定与该命令关联的会话的唯一 ID

针对这个请求的回答就十分简单了，一个简单的 `{ok: 1.0}` 响应。
到这一步，Compass 上已经弹出服务器连接成功的提示框了
接下来发的请求就是一些管理相关的命令。

同时我们的所有响应，目前都是仅仅发送一次，如果你去模拟客户端，实际情况下 针对 hello 的 响应，MongoDB 的服务器会不断地重发相同的响应内容，
这块我们留到会话管理模块的时候再实现并重构现在的代码。

# Admin Commands
```text
{
	'flagBits': 0,
	'sections': [{
		'aggregate': 1,
		'pipeline': [{
			'$currentOp': {
				'allUsers': True,
				'idleConnections': False,
				'truncateOps': False
			}
		}],
		'cursor': {},
		'lsid': {
			'id': Binary(b '\xcb\xf3\xe4\x99\xca|H\xe7\x9eqZ\xea<k\xec\x91', 4)
		},
		'$db': 'admin'
	}]
}
```
注意这些命令都是用额外的客户端端口来发送的，请求都长的大同小异。

```text
{
	'flagBits': 0,
	'sections': [{
		'cursor': {
			'firstBatch': [{
				'type': 'op',
				'host': 'LAPTOP-9CCGINFM:27017',
				'desc': 'conn10',
				'connectionId': 10,
				'client': '127.0.0.1:65120',
				'active': True,
				'currentOpTime': '2025-02-17T16:17:01.338+08:00',
				'isFromUserConnection': True,
				'threaded': True,
				'opid': 51200,
				'lsid': {
					'id': Binary(b '?\x005\x1dI\x1fD\xcd\x9d\x94\xae\xdd/\xf7\xacI', 4),
					'uid': b "\xe3\xb0\xc4B\x98\xfc\x1c\x14\x9a\xfb\xf4\xc8\x99o\xb9$'\xaeA\xe4d\x9b\x93L\xa4\x95\x99\x1bxR\xb8U"
				},
				'secs_running': 0,
				'microsecs_running': 85,
				'op': 'command',
				'ns': 'admin.$cmd.aggregate',
				'redacted': False,
				'command': {
					'aggregate': 1,
					'pipeline': [{
						'$currentOp': {
							'allUsers': True,
							'idleConnections': False,
							'truncateOps': False
						}
					}],
					'cursor': {},
					'lsid': {
						'id': Binary(b '?\x005\x1dI\x1fD\xcd\x9d\x94\xae\xdd/\xf7\xacI', 4)
					},
					'$db': 'admin'
				},
				'queryFramework': 'classic',
				'numYields': 0,
				'queues': {
					'execution': {
						'admissions': 0,
						'totalTimeQueuedMicros': 0
					},
					'ingress': {
						'admissions': 1,
						'totalTimeQueuedMicros': 0
					}
				},
				'currentQueue': None,
				'locks': {},
				'waitingForLock': False,
				'lockStats': {},
				'waitingForFlowControl': False,
				'flowControlStats': {}
			}, {
				'type': 'op',
				'host': 'LAPTOP-9CCGINFM:27017',
				'desc': 'Checkpointer',
				'active': True,
				'currentOpTime': '2025-02-17T16:17:01.338+08:00',
				'isFromUserConnection': False,
				'opid': 4131,
				'op': 'none',
				'ns': '',
				'redacted': False,
				'command': {},
				'numYields': 0,
				'queues': {
					'execution': {
						'admissions': 0,
						'totalTimeQueuedMicros': 0
					},
					'ingress': {
						'admissions': 0,
						'totalTimeQueuedMicros': 0
					}
				},
				'currentQueue': None,
				'locks': {},
				'waitingForLock': False,
				'lockStats': {},
				'waitingForFlowControl': False,
				'flowControlStats': {}
			}, {
				'type': 'op',
				'host': 'LAPTOP-9CCGINFM:27017',
				'desc': 'JournalFlusher',
				'active': True,
				'currentOpTime': '2025-02-17T16:17:01.338+08:00',
				'isFromUserConnection': False,
				'opid': 3072,
				'op': 'none',
				'ns': '',
				'redacted': False,
				'command': {},
				'numYields': 0,
				'queues': {
					'execution': {
						'admissions': 0,
						'totalTimeQueuedMicros': 0
					},
					'ingress': {
						'admissions': 0,
						'totalTimeQueuedMicros': 0
					}
				},
				'currentQueue': None,
				'locks': {},
				'waitingForLock': False,
				'lockStats': {},
				'waitingForFlowControl': False,
				'flowControlStats': {}
			}],
			'id': 0,
			'ns': 'admin.$cmd.aggregate'
		},
		'ok': 1.0
	}]
}
```

- top
具体命令参考[官方文档](https://www.mongodb.com/zh-cn/docs/manual/reference/command/top/)
```text
{
	'flagBits': 0,
	'sections': [{
		'top': 1,
		'lsid': {
			'id': Binary(b 'l\xf3\xceRD\x08I\xf9\x8bV\x14\x91\x88aDL', 4)
		},
		'$db': 'admin'
	}]
}
```

```text
{
	'flagBits': 0,
	'sections': [{
		'totals': {
			'note': 'all times in microseconds',
			'admin.$cmd.aggregate': {
				'total': {
					'time': 214,
					'count': 2
				},
				'readLock': {
					'time': 0,
					'count': 0
				},
				'writeLock': {
					'time': 0,
					'count': 0
				},
				'queries': {
					'time': 0,
					'count': 0
				},
				'getmore': {
					'time': 0,
					'count': 0
				},
				'insert': {
					'time': 0,
					'count': 0
				},
				'update': {
					'time': 0,
					'count': 0
				},
				'remove': {
					'time': 0,
					'count': 0
				},
				'commands': {
					'time': 214,
					'count': 2
				}
			},
			'admin.atlascli': {
				'total': {
					'time': 994,
					'count': 2
				},
				'readLock': {
					'time': 994,
					'count': 2
				},
				'writeLock': {
					'time': 0,
					'count': 0
				},
				'queries': {
					'time': 0,
					'count': 0
				},
				'getmore': {
					'time': 0,
					'count': 0
				},
				'insert': {
					'time': 0,
					'count': 0
				},
				'update': {
					'time': 0,
					'count': 0
				},
				'remove': {
					'time': 0,
					'count': 0
				},
				'commands': {
					'time': 994,
					'count': 2
				}
			},
			'admin.system.version': {
				'total': {
					'time': 182,
					'count': 1
				},
				'readLock': {
					'time': 182,
					'count': 1
				},
				'writeLock': {
					'time': 0,
					'count': 0
				},
				'queries': {
					'time': 0,
					'count': 0
				},
				'getmore': {
					'time': 0,
					'count': 0
				},
				'insert': {
					'time': 0,
					'count': 0
				},
				'update': {
					'time': 0,
					'count': 0
				},
				'remove': {
					'time': 0,
					'count': 0
				},
				'commands': {
					'time': 0,
					'count': 0
				}
			},
			'config.system.sessions': {
				'total': {
					'time': 4364,
					'count': 21
				},
				'readLock': {
					'time': 895,
					'count': 16
				},
				'writeLock': {
					'time': 3469,
					'count': 5
				},
				'queries': {
					'time': 0,
					'count': 0
				},
				'getmore': {
					'time': 0,
					'count': 0
				},
				'insert': {
					'time': 0,
					'count': 0
				},
				'update': {
					'time': 0,
					'count': 0
				},
				'remove': {
					'time': 3469,
					'count': 5
				},
				'commands': {
					'time': 895,
					'count': 16
				}
			},
			'config.transactions': {
				'total': {
					'time': 1137,
					'count': 8
				},
				'readLock': {
					'time': 1137,
					'count': 8
				},
				'writeLock': {
					'time': 0,
					'count': 0
				},
				'queries': {
					'time': 1137,
					'count': 8
				},
				'getmore': {
					'time': 0,
					'count': 0
				},
				'insert': {
					'time': 0,
					'count': 0
				},
				'update': {
					'time': 0,
					'count': 0
				},
				'remove': {
					'time': 0,
					'count': 0
				},
				'commands': {
					'time': 0,
					'count': 0
				}
			},
			'local.startup_log': {
				'total': {
					'time': 1577,
					'count': 2
				},
				'readLock': {
					'time': 1577,
					'count': 2
				},
				'writeLock': {
					'time': 0,
					'count': 0
				},
				'queries': {
					'time': 0,
					'count': 0
				},
				'getmore': {
					'time': 0,
					'count': 0
				},
				'insert': {
					'time': 0,
					'count': 0
				},
				'update': {
					'time': 0,
					'count': 0
				},
				'remove': {
					'time': 0,
					'count': 0
				},
				'commands': {
					'time': 1577,
					'count': 2
				}
			},
			'local.system.replset': {
				'total': {
					'time': 14,
					'count': 1
				},
				'readLock': {
					'time': 14,
					'count': 1
				},
				'writeLock': {
					'time': 0,
					'count': 0
				},
				'queries': {
					'time': 0,
					'count': 0
				},
				'getmore': {
					'time': 0,
					'count': 0
				},
				'insert': {
					'time': 0,
					'count': 0
				},
				'update': {
					'time': 0,
					'count': 0
				},
				'remove': {
					'time': 0,
					'count': 0
				},
				'commands': {
					'time': 0,
					'count': 0
				}
			}
		},
		'ok': 1.0
	}]
}
```
readLock 和 writeLock 指的是读写锁的持有时间和次数。
很明显是和多客户端并发读写一致性相关的东西，现阶段还不需要（其实是不会写）
这样的话我们的返回就很简单了，遍历每一个存在的集合返回一个全部都是 0 的集合就完了。

- buildInfo
```text
{
	'flagBits': 0,
	'sections': [{
		'version': '8.0.4',
		'gitVersion': 'bc35ab4305d9920d9d0491c1c9ef9b72383d31f9',
		'targetMinOS': 'Windows 7/Windows Server 2008 R2',
		'modules': [],
		'allocator': 'tcmalloc-gperf',
		'javascriptEngine': 'mozjs',
		'sysInfo': 'deprecated',
		'versionArray': [8, 0, 4, 0],
		'openssl': {
			'running': 'Windows SChannel'
		},
		'buildEnvironment': {
			'distmod': 'windows',
			'distarch': 'x86_64',
			'cc': 'cl: Microsoft (R) C/C++ Optimizing Compiler Version 19.31.31107 for x64',
			'ccflags': '/nologo /WX /FImongo/platform/basic.h /fp:strict /EHsc /W3 /wd4068 /wd4244 /wd4267 /wd4290 /wd4351 /wd4355 /wd4373 /wd4800 /wd4251 /wd4291 /we4013 /we4099 /we4930 /errorReport:none /MD /O2 /Oy- /bigobj /utf-8 /permissive- /Zc:__cplusplus /Zc:sizedDealloc /volatile:iso /diagnostics:caret /std:c++20 /Gw /Gy /Zc:inline',
			'cxx': 'cl: Microsoft (R) C/C++ Optimizing Compiler Version 19.31.31107 for x64',
			'cxxflags': '/TP',
			'linkflags': '/nologo /DEBUG /INCREMENTAL:NO /LARGEADDRESSAWARE /OPT:REF',
			'target_arch': 'x86_64',
			'target_os': 'windows',
			'cppdefines': 'SAFEINT_USE_INTRINSICS 0 PCRE2_STATIC NDEBUG BOOST_ALL_NO_LIB _UNICODE UNICODE _SILENCE_CXX17_ALLOCATOR_VOID_DEPRECATION_WARNING _SILENCE_CXX17_OLD_ALLOCATOR_MEMBERS_DEPRECATION_WARNING _SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING _SILENCE_ALL_CXX20_DEPRECATION_WARNINGS _CONSOLE _CRT_SECURE_NO_WARNINGS _ENABLE_EXTENDED_ALIGNED_STORAGE _SCL_SECURE_NO_WARNINGS _WIN32_WINNT 0x0A00 BOOST_USE_WINAPI_VERSION 0x0A00 NTDDI_VERSION 0x0A000000 ABSL_FORCE_ALIGNED_ACCESS BOOST_ENABLE_ASSERT_DEBUG_HANDLER BOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF BOOST_LOG_NO_SHORTHAND_NAMES BOOST_LOG_USE_NATIVE_SYSLOG BOOST_LOG_WITHOUT_THREAD_ATTR BOOST_MATH_NO_LONG_DOUBLE_MATH_FUNCTIONS BOOST_SYSTEM_NO_DEPRECATED BOOST_THREAD_USES_DATETIME BOOST_THREAD_VERSION 5'
		},
		'bits': 64,
		'debug': False,
		'maxBsonObjectSize': 16777216,
		'storageEngines': ['devnull', 'wiredTiger'],
		'ok': 1.0
	}]
}
```

- hostInfo

```text
{
	'flagBits': 0,
	'sections': [{
		'system': {
			'currentTime': datetime.datetime(2025, 2, 17, 8, 17, 1, 340000),
			'hostname': 'LAPTOP-9CCGINFM',
			'cpuAddrSize': 64,
			'memSizeMB': 32386,
			'memLimitMB': 32386,
			'numCores': 32,
			'numCoresAvailableToProcess': 32,
			'numPhysicalCores': 24,
			'numCpuSockets': 1,
			'cpuArch': 'x86_64',
			'numaEnabled': False,
			'numNumaNodes': 1
		},
		'os': {
			'type': 'Windows',
			'name': 'Microsoft Windows 10',
			'version': '10.0 (build 22631)'
		},
		'extra': {
			'pageSize': 4096,
			'cpuString': 'Intel(R) Core(TM) i9-14900HX'
		},
		'ok': 1.0
	}]
}
```

- getParameter
`{'getParameter': 1, 'featureCompatibilityVersion': 1}`
- atlasVersion
`{'atlasVersion': 1}`
抓包看的是返回了一个 error msg 的格式，内容是没有这个命令
- connectionStatus
`{'connectionStatus': 1, 'showPrivileges': True}`
```text
{
	'flagBits': 0,
	'sections': [{
		'aggregate': 'atlascli',
		'pipeline': [{
			'$match': {
				'managedClusterType': 'atlasCliLocalDevCluster'
			}
		}, {
			'$group': {
				'_id': 1,
				'n': {
					'$sum': 1
				}
			}
		}],
		'cursor': {},
		'lsid': {
			'id': Binary(b '\xdf\xc3\xa1\xb4\t]@\x90\x89\xc0hx`\xb4+\xa7', 4)
		},
		'$db': 'admin'
	}]
}
```
- listDatabases
`{'listDatabases: 1, 'nameOnly': True}`
很显然返回所有的数据库集合
- dbStats
`{'dbStats': 1}`



# EndSession
如果你手动的终止 Compass 客户端与服务端的连接，那么服务端会收到一个我叫做 EndSession 的请求。
它看起来像下面这样，如果仔细观察，你会发现它的 sections 数组中包含了所有当前连接的 session 的 id。
```text
{
	'flagBits': 0,
	'sections': [{
		'endSessions': [{
			'id': Binary(b '}\xa6\x18\xa6\x18\xccIl\xb2!\x84\xdf\x8e0\x13\xc6', 4)
		}, {
			'id': Binary(b '\no\x13W\x0c\x07H\x93\x9bPqD\x9a\x7f\x86\xf5', 4)
		}, {
			'id': Binary(b '\x00\x8bO\xff,\x89E\xe4\xb2m\xc3\x8c!7Z\xbe', 4)
		}, {
			'id': Binary(b '\x8f\xdf\xe0\x07\xdbpI\xbe\xac\r\xcdb\x0e\x9f*E', 4)
		}, {
			'id': Binary(b '\x85l\x08\x14\x99z@\xc3\xa6\x19\xae\xb0\x8f\r\xce\xa2', 4)
		}, {
			'id': Binary(b '\xe7EbJ\x11\x91K\xc7\xb1\xff\xf9\xc3\x81J\xdem', 4)
		}, {
			'id': Binary(b '\xde0bQ#cM\xe9\x90\xd1\x16\xc3[\xca\xa9C', 4)
		}, {
			'id': Binary(b '\x11\xc0o\xe3\x7f\x02H:\x80\xe8"\n\x1b\xdc\xf2\xc1', 4)
		}, {
			'id': Binary(b '\x03\r\x94\x82lFF\x92\xa1Z\x8dV\xf3O\x0b<', 4)
		}, {
			'id': Binary(b '\xcap\xc6\x940\xf2G\xa5\xa3\x83\x10UC\xa8>\x89', 4)
		}, {
			'id': Binary(b 'l\xf3\xceRD\x08I\xf9\x8bV\x14\x91\x88aDL', 4)
		}, {
			'id': Binary(b '\x9c\xc0\xbc\xe2}\xabJ\xf3\xa4>\xf6Q!\xe1\xfe~', 4)
		}, {
			'id': Binary(b '\xdf\xc3\xa1\xb4\t]@\x90\x89\xc0hx`\xb4+\xa7', 4)
		}, {
			'id': Binary(b '\xc6\x13\x04\x95\xc2\x94G\x00\xac\x11\nc\x9dz@\xde', 4)
		}],
		'lsid': {
			'id': Binary(b '}\xa6\x18\xa6\x18\xccIl\xb2!\x84\xdf\x8e0\x13\xc6', 4)
		},
		'$db': 'admin'
	}]
}
```
涉及到会话的管理，目前我们还没有做，先搁置一下吧。
> endSessions 命令将会话标记为已过期，以向服务器发出信号以清理会话并更新会话的过期时间。该命令会覆盖会话在过期之前等待的超时时间。

