import sys
import struct
import random
from ..protocol.transmit import TCPClientTransmit, TransmitException


# Server: libembcore.unittest.tcp_server --address=0.0.0.0:8000 --with_length
if __name__ == '__main__':
    port = 8000
    server = '192.168.8.5'
    client = TCPClientTransmit(length_fmt='>L')

    if len(sys.argv) >= 3:
        server = sys.argv[1]
        port = int(sys.argv[2])

    print(f'Server: {server}:{port}')

    try:
        client.connect((server, port), 1.0)
    except TransmitException as e:
        print(f'Connect fail: {e}')
        sys.exit(0)

    min_size = 1024
    max_size = 1024 * 1024
    total_send_size = 0
    random_data = bytes([random.randint(0, 255) for _ in range(max_size)])
    print(len(random_data))
    client.tx(b'SPEED_TEST')

    while True:
        size = random.randint(min_size, max_size)
        if not client.tx(random_data[:size]):
            print(f'Send error size: {size}')
            break

        total_send_size += size
        peer_rx_size = struct.unpack('<Q', client.rx(0))[0]
        if total_send_size != peer_rx_size:
            print(f'Tx: {total_send_size}, Rx: {peer_rx_size}')
            break
