import asyncio
import threading
import queue
import socket
from typing import Callable, Tuple

class AioSocker:
    def __init__(self):
        self._new_socket_q = asyncio.Queue()
        self._new_queue_q = queue.Queue()
        self._socket_transports = {}
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

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
        task = asyncio.create_task(
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

if __name__ == "__main__":
    sockman = AioSocker()

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

