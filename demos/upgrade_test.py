# -*- coding: utf-8 -*-

import sys
from ..protocol.upgrade import UpgradeClient, UpgradeServer


def client_test(name, server, port):
    test_cnt = 10
    upgrade_check = UpgradeClient(name, server, int(port))

    # Check connection_status
    if not upgrade_check.is_connected():
        print("Connection is failed!")
        sys.exit(-1)

    # If there's new version
    print(upgrade_check.has_new_version(0.7))

    while test_cnt > 0:
        print("{0:02d} Info is:{1}".format(test_cnt, upgrade_check.get_new_version_info()))
        test_cnt -= 1


def server_test(root=UpgradeServer.FILE_SERVER_ROOT):
    # Create a tcp server
    server = UpgradeServer(file_server_root=root)
    server.serve_forever()

if __name__ == '__main__':
    # Client mode
    if len(sys.argv) == 4:
        client_test(sys.argv[1], sys.argv[2], sys.argv[3])
    # Server mode default root
    elif len(sys.argv) == 2 and sys.argv[1] == "server":
        server_test()
    # Server mode specified root
    elif len(sys.argv) == 3 and sys.argv[1] == "server":
        server_test(sys.argv[2])
    else:
        print("Usage: {0:s} <server> [root]".format(sys.argv[0]))
        print("Usage: {0:s} <software_name> <server_address> <server_port>".format(sys.argv[0]))
        sys.exit(-1)
