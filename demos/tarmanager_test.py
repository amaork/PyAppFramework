# -*- coding: utf-8 -*-

import os
import sys
import getopt
from ..misc.tarmanager import TarManager


def usage():
    print "\n{0:s} -c[x] -s xxx -d xxx -f xxx\n".format(os.path.basename(sys.argv[0]))
    print "\t-h\--help\tshow this help menu"
    print "\t-v\--verbose\toutput verbose message"
    print "\t-c\--create\tcreate a package file"
    print "\t-x\--extract\textract a package file"
    print "\t-s\--src\tspecify will package file path or will extract file path"
    print "\t-d\--dest\tspecify package file name or will extract file  path"
    print "\t-x\--format\tspecify package file format: {0:s}".format(TarManager.get_support_format())


if __name__ == '__main__':

    try:

        opts, args = getopt.getopt(sys.argv[1:], "hcxvf:s:d:", ["help", "create", "extract", "verbose",
                                                                "format=", "src=", "dest="])
        formats = ""
        verbose = False
        src_path = ""
        dest_path = ""
        package_operate = False
        unpackage_operate = False

        for option, argument in opts:
            # Create a package
            if option in ("-c", "--create"):
                package_operate = True

            # Extract a package
            elif option in ("-x", "--extract"):
                unpackage_operate = True

            # Verbose message output
            elif option in ("-v", "--verbose"):
                verbose = True

            # Show help message
            elif option in ("-h", "--help"):
                usage()
                sys.exit()

            # Format setting
            elif option in ("-f", "--format") and len(argument):
                if argument not in TarManager.get_support_format():
                    print "Unknown format:{0:s}".format(argument)
                    usage()
                    sys.exit()

                formats = argument

            # Get src file, for package operate, src is will package directory,
            # for unpackage operate, src is will unpackaged file
            elif option in ("-s", "--src") and len(argument):
                src_path = argument

            elif option in ("-d", "--dest") and len(argument):
                dest_path = argument

        # Operate check
        if not package_operate and not unpackage_operate:
            print "You must specified a operate package(-c/--create) or unpackage(-x/--extract)"
            usage()
            sys.exit()

        if package_operate and unpackage_operate:
            print "Conflicting options: -c[--create], -x[--extract], they can't specified at same time"
            usage()
            sys.exit(-1)

        # Format check
        if len(formats) == 0:
            print "You must specified a format (-f/--format=):{0:s}".format(TarManager.get_support_format())
            usage()
            sys.exit()

        # Check src and dest
        if len(src_path) == 0:
            print "You must specified a source path, -s/--src"
            usage()
            sys.exit()

        if len(dest_path) == 0:
            print "You must specified a dest path, -d/--dest"
            usage()
            sys.exit()

        # Operate
        if package_operate:
            print TarManager.pack(src_path, dest_path, formats, verbose)

        if unpackage_operate:
            print TarManager.unpack(src_path, fmt=formats)

    except getopt.GetoptError, e:
        print "Error:{0:s}".format(e)
        usage()
        sys.exit()
