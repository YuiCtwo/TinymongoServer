import logging

__all__ = ["server_logger"]

server_logger = logging.getLogger("tinymongo_server")
_server_logger_handler = logging.FileHandler("tinymongo_server.log")
_server_logger_handler.setLevel(logging.INFO)
# record thread id in file
server_logger_formatter = logging.Formatter(
    "[%(thread)d] %(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
_server_logger_handler.setFormatter(server_logger_formatter)
server_logger.addHandler(
    _server_logger_handler
)
server_logger.setLevel(logging.INFO)
