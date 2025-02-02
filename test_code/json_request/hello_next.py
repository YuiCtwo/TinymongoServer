from bson import ObjectId

payload = {
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
}