# Socket Manager
The SockMan class is an asycnchronous manager of sockets.

## Instantiation
When SockMan is instantiated, it will start an internally managed thread. The thread will use asyncio to
manage several sockets that will be added later.

SockMan takes no further actions until given sockets to manage.

## API
SockMan has a some methods for getting data from sockets.

### start_receiving_on
`start_receiving_on` takes in a pre-configured, and opened, socket and returns a queue and a stop function.

SockMan adds the socket to it's internal container of sockets that it is calling recv on. When UDP data is received
from this socket, it is written into the queue.

If the returned stop function is called, SockMan will no longer attempt to interact with the socket. The stop
function will not return until SockMan has fully released control of the socket.