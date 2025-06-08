import asyncio
import threading
import queue
import socket
from typing import Callable, Tuple

class SockMan:
    def __init__(self):
        # create a thread to run our asyncio event loop
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def __del__(self):
        self._loop.stop()

    def _run_event_loop(self):
        # within the loop's thread
        # create our event loop
        self._loop = asyncio.new_event_loop()
        # and set it as the event loop for this thread
        asyncio.set_event_loop(self._loop)

        # start the loop
        self._loop.run_forever()
        # if the loop ever exits, lets close it
        self._loop.close()

    class _handler(asyncio.DatagramProtocol):
        """_handler implements the DatagramProtocol

        This allows us to give it to asyncio as a datagram endpoint
        and define the behavior we want asyncio to take every time
        a UDP packet is received
        """
        def __init__(self, q: queue.Queue):
            self.q = q

        def datagram_received(self, data, addr):
            # when a datagram is received, we just want to stick in the queue
            # to let someone else process it
            self.q.put(data)

    async def _start_rx_task(self, sock: socket.socket) -> Tuple[queue.Queue, Callable]:
        """_start_rx_task manages the creation of a new rx task by taking in a configured
        socket and returing a queue and stop function.

        A new rx task is created to receive data from a new socket. The task will
        listen for data on the socket, and put any received data into the queue that
        we return on creation.

        Calling the returned stop function will cause the task to terminate, freeing the socket.
        """
        new_q = queue.Queue()

        # create a new task in our event loop that listens for data on sock
        task = self._loop.create_task(
            self._loop.create_datagram_endpoint(
                # lambda is used here because create_datagram_endpoint needs to be given a function that
                # generates an implementation of DatagramProtocol. lambda is simply wrapping the
                # instantiation of our _handler class with the queue that was created for this socket's data
                lambda: self._handler(new_q),
                sock=sock,
            )
        )

        # create a closure that will call cancel on our new task.
        def stop():
            # because this closure will be called from a non-async context,
            # we need to use call_soon_threadsafe to inject the call to
            # task.cancel into the async event loop
            self._loop.call_soon_threadsafe(task.cancel)

        return new_q, stop

    def start_receiving_on(self, sock: socket.socket) -> Tuple[queue.Queue, Callable]:
        """Provide a configured socket for SockMan to start using to receive UDP packets.

        Received UDP packets will be available in the returned queue.
        The returned callable is a function to stop the receive task.
        """
        # To allow start_receiving_on to be called from a non-async context and be able
        # to get the returned queue and stop(), we use run_coroutine_threadsafe to schedule
        # self._start_rx_task to be run in the self._loop
        future = asyncio.run_coroutine_threadsafe(self._start_rx_task(sock), self._loop)
        # future.result() will block until the coroutine has completed and will pass the
        # coroutine's return
        return future.result()

def test_many_ports():
    """Quick test to demonstrate being able to concurrently listen on 100 ports
    """
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

