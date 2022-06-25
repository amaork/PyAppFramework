# -*- coding: utf-8 -*-
import sys
import time
import getopt
from ..core.datatype import str2float, str2number
from ..network.proxy import ProxyAttribute, TransparentProxy


if __name__ == '__main__':
    try:
        attr = ProxyAttribute(address='', port=0)
        opts, args = getopt.getopt(sys.argv[1:], '', [f'{x}=' for x in ProxyAttribute.properties()])

        for option, argument in opts:
            option = option[2:]
            if option in ProxyAttribute.properties():
                if option in ('port', 'recv_buf_size'):
                    argument = str2number(argument)

                if option in ('timeout',):
                    argument = str2float(argument)

                attr.update({option: argument})

        if not attr.address:
            raise getopt.GetoptError('must specified an address')

        if not attr.port:
            raise getopt.GetoptError('must specified a port')

        print(f'Start transparent proxy: {attr}')
        proxy = TransparentProxy(attribute=attr)
        while True:
            time.sleep(1)
    except getopt.GetoptError as e:
        print(f'Get option error: {e}\n')
        print(f'{sys.argv[0]} usage:\n'
              f'\t{"--address":15}set server address\n'
              f'\t{"--port":15}set server port\n'
              f'\t{"--timeout":15}set timeout\n')
        sys.exit()
