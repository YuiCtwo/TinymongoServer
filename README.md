# TinymongoServer

An extension version of [Tinymongo](https://github.com/schapman1974/tinymongo) which supports connection from local or remote server.

This repo is a learning project to write a database server by oneself.
There is so many things to learn from the official drivers: https://github.com/mongodb/mongo-python-driver


# Environment Setup

Run the following command in your project directory:
```
pip install -e git+https://github.com/schapman1974/tinymongo.git#egg=tinymongo
```
The source code of Tinymongo will be downloaded at `/src/tinymongo`.
Then, `bson` is required to be installed to parse and serialize BSON documents.
```
pip install bson
```

# Usage

Up to now, you can use our implemented server by running: `python tinymongo_server.py`

Parameters:
- `--host`: the host address of the server,default: `127.0.0.1`
- `--port`: the port number of the server, default: `27018`, as `27017` is officially used by MongoDB.

Then, try connecting to the server using some clients like **Mongodb Compass**.

# Acknowledgements

Thanks to these great projects, our work is build on top of them:

- [Tinymongo](https://github.com/schapman1974/tinymongo)