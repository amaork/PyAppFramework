# -*- coding: utf-8 -*-
"""
Tar package file manager, support package file/directory to tar, gz, bz2  or unpackage file
"""


import os
import shutil
import tarfile


__all__ = ['TarManager', 'TarManagerError']


class TarManagerError(Exception):
    pass


class TarManager(object):
    formatDict = {
        "tar": ":",
        "gz": ":gz",
        "tgz": ":gz",
        "bz2": ":bz2",
        "tbz2": ":bz2",
    }

    operateDict = {
        "read": "r",
        "write": "w",
    }

    def __init__(self):
        pass

    @staticmethod
    def get_file_format(name):
        """Get file format

        :param name: file name
        :return: file format
        """

        name = os.path.basename(name)
        formats = os.path.splitext(name)[-1][1:]
        return formats if formats in list(TarManager.formatDict.keys()) else ""

    @staticmethod
    def get_support_format():
        return list(TarManager.formatDict.keys())

    @staticmethod
    def __core_pack(tar, path, verbose):
        if not isinstance(tar, tarfile.TarFile) or not os.path.isfile(path):
            return

        if verbose:
            print(path[2:])

        tar.add(path)

    @staticmethod
    def pack(path, name, fmt=None, extensions=None, filters=None, verbose=False):
        """Package directory to a tarfile

        :param path: directory path
        :param name: package name
        :param fmt: package formats
        :param extensions: if set only pack those extension names
        :param filters: if set when filter is true will packed
        :param verbose: show verbose message
        """

        current_path = os.getcwd()
        filters = filters if hasattr(filters, "__call__") else None
        extensions = extensions if isinstance(extensions, (list, tuple)) else list()

        try:

            # Make sure path is a dir
            if not os.path.isdir(path):
                raise TarManagerError("Path: {0:s} is not a directory".format(path))

            # Check name
            if not os.path.isdir(os.path.dirname(name)):
                name = os.path.join(current_path, os.path.basename(name))

            # Get file format
            formats = fmt if fmt in TarManager.get_support_format() else TarManager.get_file_format(name)

            if len(formats) == 0:
                raise TarManagerError("Unknown package format: {}".format(os.path.basename(name)))

            # Entry package directory
            os.chdir(path)

            # Create package file
            tar_file = tarfile.open(name, TarManager.operateDict.get("write") + TarManager.formatDict.get(formats))

            # Print package info
            if verbose:
                print("{0:s} -> {1:s}".format(os.path.abspath(path), name))

            # Traversal all files in path add to tarFile
            for root, dirs, files in os.walk('.'):
                for file_name in files:
                    extension_name = file_name.split(".")[-1]
                    full_path = os.path.join(root, file_name)

                    # File extension name is in extension
                    if len(extensions) and extension_name in extensions:
                        TarManager.__core_pack(tar_file, full_path, verbose)
                        continue

                    # File name is pass the filter
                    if filters and filters(extension_name):
                        TarManager.__core_pack(tar_file, full_path, verbose)
                        continue

                    # No in extensions and not in filters
                    if len(extensions) or filters:
                        continue

                    # Do not has extension and filters pack all
                    TarManager.__core_pack(tar_file, full_path, verbose)

            # Close tarFile
            tar_file.close()

        except OSError as e:
            raise TarManagerError("Change work dir error:{}".format(e))
        except tarfile.TarError as e:
            raise TarManagerError("Create tar file error:{}".format(e))
        finally:
            os.chdir(current_path)

    @staticmethod
    def unpack(file_path, unpack_path="", fmt=None):
        """Unpack file_path specified file to unpack_path

        :return:
        :param file_path: Tar file path
        :param unpack_path: Unpack path
        :param fmt: package format
        """
        try:

            # Check tar file path
            if not os.path.isfile(file_path):
                raise TarManagerError("Tarfile: {0:s} is not exist".format(file_path))

            # Check tar file format
            if not tarfile.is_tarfile(file_path):
                raise TarManagerError("Package:{0:s} is not a tarfile".format(file_path))

            # Get file format
            formats = fmt if fmt in TarManager.get_support_format() else TarManager.get_file_format(file_path)

            if len(formats) == 0:
                raise TarManagerError("Unknown package format:{0:s}".format(file_path))

            # Check unpack directory
            if len(unpack_path) == 0:
                unpack_path = os.path.splitext(os.path.basename(file_path))[0]

            if not os.path.isdir(unpack_path):
                os.makedirs(unpack_path)

            # Open as tarfile and extractall and close finally
            tar_file = tarfile.open(file_path, TarManager.operateDict.get("read") + TarManager.formatDict.get(formats))
            tar_file.extractall(unpack_path)
            tar_file.close()

        except (IOError, OSError, tarfile.TarError, shutil.Error) as e:
            raise TarManagerError('Extract failed：IOError, {}'.format(e))

