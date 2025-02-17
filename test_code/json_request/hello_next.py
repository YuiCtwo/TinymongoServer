from bson import ObjectId, int64
payload = {
	'flagBits': 65536,
	'sections': [{
		'hello': 1,
		'maxAwaitTimeMS': 10000,
		'topologyVersion': {
			'processId': ObjectId(),
			'counter': int64.Int64(0)
		},
		'$db': 'admin'
	}]
}