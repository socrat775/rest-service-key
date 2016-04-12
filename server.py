import socket, re, logging
from tornado.gen import coroutine, Return
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer as AsyncTCPServer
from motor import MotorClient
from random import choice


class HandlerClient(object):
    def __init__(self, stream, address, db):
        self.stream = stream
        self.address = address
        self.collection = db.test.all_keys
        self.all_state = {0: b"not issued", 1: b"issued", 2: b"repaid"}
        self.stream.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.stream.set_close_callback(self.close_connect)

    @coroutine
    def on_connect(self):
        logging.debug("new connect: %s", self.address)
        yield self.handler_request()

    @coroutine
    def get_key(self):
        logging.debug("get key")
        random_key = yield self.collection.find_one({"status": 0})
        update_key = yield self.collection.update({"key": random_key['key']}, {"$set": {"status": 1}})
        logging.debug("Update key %s: %s", random_key, update_key)
        raise Return(random_key)      

    @coroutine
    def repay_key(self, key):
        logging.debug("repay key: %s", key)
        check_key = yield self.collection.find_one({"key": key})
        if check_key['status'] == 1:
           result = yield self.collection.update({"key": key}, {"$set": {"status": 2}})
           raise Return("repayed success")
        else:
           logging.warning("key '%s' not repayed from: %s", key, self.address)
           raise Return("key not repayed")

    @coroutine
    def check_key(self, key):
        logging.debug("check key: %s", key)
        state = yield self.collection.find_one({"key": key})
        raise Return(state['status'])

    @coroutine
    def info_keys(self):
        logging.debug("info keys")
        info = self.collection.find({"status": 0})
        count = yield info.count()
        raise Return(count)

    @coroutine
    def handler_request(self):
        try:
           data = yield self.stream.read_bytes(8)
           command, key = data.split(":")
           logging.debug("COMMAND: %s, KEY: %s", command, key)
           if command == b"GET":
              result = yield self.get_key()
              yield self.stream.write(bytes(result['key']))
           elif command == b"REP" and len(re.findall(r'[A-Za-z0-9]', key)) == 4:
              result = yield self.repay_key(key)
              yield self.stream.write(bytes(result))
           elif command == b"CHE" and len(re.findall(r'[A-Za-z0-9]', key)) == 4:
              result = yield self.check_key(key)
              yield self.stream.write(self.all_state[result])
           elif command == b"INF":
              result = yield self.info_keys()
              yield self.stream.write(bytes(result))
           else:
              logging.warning("unknown request from: %s", self.address)
              yield self.stream.close()
        except StreamClosedError:
           logging.warning("StreamClosedError")

    def close_connect(self):
        logging.debug("Disconnected from: %s", self.address)

class RESTserver(AsyncTCPServer):
    db = MotorClient('localhost', 27017)

    @coroutine
    def handle_stream(self, stream, address):
        connection = HandlerClient(stream, address, RESTserver.db)
        yield connection.on_connect()

if __name__ == "__main__":
   logging.basicConfig(format="%(lineno)s:%(levelname)s ==> %(message)s", level=logging.DEBUG)
   server = RESTserver()
   host, port = "127.0.0.2", 8888
   server.listen(port, host)
   logging.info("Server started with %s:%s", host, port)
   IOLoop.current().start()

