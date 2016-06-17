# -*- coding: utf-8 -*-

import sys
import threading
from ..protocol.upgrade import UpgradeClient, UpgradeServer, UpgradeServerHandler


def client_test(name, server, port):
    test_cnt = 10
    upgrade_check = UpgradeClient(name, server, int(port))

    # Check connection_status
    if not upgrade_check.is_connected():
        print "Connection is failed!"
        sys.exit(-1)

    # If there's new version
    print upgrade_check.has_new_version(0.7)

    while test_cnt > 0:
        print "{0:02d} Info is:{1:s}".format(test_cnt, upgrade_check.get_new_version_info())
        test_cnt -= 1


def server_test():
    # Server setting
    HOST, PORT = '0.0.0.0', 9999

    # Create a tcp server
    server = UpgradeServer((HOST, PORT), UpgradeServerHandler)

    # Start thread with the server
    server_thread = threading.Thread(target=server.serve_forever)

    # Start server
    server_thread.start()

    # Print info
    print "Software upgrade multi-threading server is running!"


if __name__ == '__main__':
    if len(sys.argv) == 4:
        client_test(sys.argv[1], sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 2 and sys.argv[1] == "server":
        server_test()
    else:
        print "Usage: {0:s} server"
        print "Usage: {0:s} software_name, server_address, server_port".format(sys.argv[0])
        sys.exit(-1)