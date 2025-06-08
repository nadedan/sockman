import asyncio
import threading
import queue
import socket
from typing import Callable, Tuple

class SockMan:
    def __init__(self):
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def __del__(self):
        self._loop.stop()

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._loop.run_forever()
        self._loop.close()

    class _handler(asyncio.DatagramProtocol):
        def __init__(self, q: queue.Queue):
            self.q = q

        def datagram_received(self, data, addr):
            self.q.put(data)

    async def _start_rx_task(self, sock: socket.socket) -> Tuple[queue.Queue, Callable]:
        new_q = queue.Queue()
        task = self._loop.create_task(
            self._loop.create_datagram_endpoint(
                lambda: self._handler(new_q),
                sock=sock,
            )
        )

        def stop():
            self._loop.call_soon_threadsafe(task.cancel)

        return new_q, stop

    def start_receiving_on(self, sock: socket.socket) -> Tuple[queue.Queue, Callable]:
        future = asyncio.run_coroutine_threadsafe(self._start_rx_task(sock), self._loop)
        return future.result()

def test_many_ports():
    sockman = SockMan()
    ques = {}
    for i in range(100):
        port = 9000 + i

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', port))

        ques[port] = sockman.start_receiving_on(sock)

    p = 1
    while True:
        p = input("Enter port to read: ")
        p = int(p)
        if p == 0:
            quit()
        q, stop = ques[p]
        d = q.get()
        print(d.decode())

if __name__ == "__main__":
    test_many_ports()

    sockman = SockMan()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 9000))

    q, stop = sockman.start_receiving_on(sock)

    count = 0
    while count < 5:
        try:
            d = q.get(timeout=1)
        except queue.Empty:
            print("nothing")
        else:
            count+=1
            print(d)

    print("stopping")
    stop()
    print("stopped")

