import uuid
import bson
payload_agg = {
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
            'id': bson.Binary.from_uuid(uuid.uuid4())
        },
        '$db': 'admin'
    }]
}

payload_buildInfo = {
	'flagBits': 0,
	'sections': [{
		'buildInfo': 1,
		'lsid': {
			'id': bson.Binary.from_uuid(uuid.uuid4())
		},
		'$db': 'admin'
	}]
}

payload_top = {
	'flagBits': 0,
	'sections': [{
		'top': 1,
		'lsid': {
			'id': bson.Binary.from_uuid(uuid.uuid4())
		},
		'$db': 'admin'
	}]
}

payload_hostInfo = {
    'flagBits': 0,
    'sections': [{
        'hostInfo': 1,
        'lsid': {
            'id': bson.Binary.from_uuid(uuid.uuid4())
        },
        '$db': 'admin'
    }]
}