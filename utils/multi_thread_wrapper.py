import threading
import time

class CommonThread(threading.Thread):
    def __init__(self, client, response_raw):
        super(CommonThread, self).__init__()
        self.client = client
        self.response_raw = response_raw
        self.daemon = True

    def run(self):
        self.client.sendall(self.response_raw)

class LoopThread(threading.Thread):

    def __init__(self, interval_ms, client, response_raw):
        super(LoopThread, self).__init__()
        self.interval = interval_ms
        # end when the main thread exits
        self.daemon = True
        self.client = client
        self.response_raw = response_raw

    def run(self):
        while True:
            self.client.sendall(self.response_raw)
            print("[LoopThread]: sending response")
            # sleep for interval seconds
            time.sleep(self.interval / 1000.0)