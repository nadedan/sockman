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

        self._loop.run_until_complete(self._get_and_start_sockets())
        self._loop.close()

    class _handler(asyncio.DatagramProtocol):
        def __init__(self, q: queue.Queue):
            self.q = q

        def datagram_received(self, data, addr):
            self.q.put(data)

    async def _get_and_start_sockets(self):
        while True:
            this_socket = await self._new_socket_q.get()
            new_q = queue.Queue()
            async def rx_task():
                transport, _protocol = await self._loop.create_datagram_endpoint(
                    lambda: self._handler(new_q),
                    sock=this_socket,
                )
                self._socket_transports[this_socket] = transport
                while True:
                    await asyncio.sleep(0.1) #keep the loop running
                #
            #
            task = asyncio.create_task(rx_task())

            def stop():
                self._loop.call_soon_threadsafe(self._socket_transports[this_socket].close())
                self._loop.call_soon_threadsafe(task.cancel)
                self._socket_transports.pop(this_socket, None)

            self._new_queue_q.put((new_q, stop))

    def start_receiving_on(self, sock: socket.socket) -> Tuple[queue.Queue, Callable]:
        asyncio.run_coroutine_threadsafe(self._new_socket_q.put(sock), self._loop)
        return self._new_queue_q.get()

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

