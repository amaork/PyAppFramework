# -*- coding: utf-8 -*-
"""
Tar package file manager, support package file/directory to tar, gz, bz2  or unpackage file
"""


import os
import shutil
import tarfile
import zipfile


__all__ = ['TarManager', 'TarManagerError']


class Compress(object):
    exception = Exception
    support_format = {}

    def open(self, name, mode, fmt):
        pass

    def close(self, obj):
        if not self.type_check(obj):
            return

        self._close(obj)

    def _close(self, obj):
        pass

    def type_check(self, obj):
        pass

    def file_check(self, file):
        pass

    def _pack(self, obj, filename):
        pass

    def pack(self, obj, filename):
        if not self.type_check(obj) or not os.path.isfile(filename):
            return

        self._pack(obj, filename)

    def _extractall(self, obj, extract_path):
        pass

    def extractall(self, obj, extract_path):
        if not self.type_check(obj):
            return False

        self._extractall(obj, extract_path)


class TarCompress(Compress):
    exception = tarfile.TarError
    support_format = {
        "tar": ":",
        "gz": ":gz",
        "tgz": ":gz",
        "bz2": ":bz2",
        "tbz2": ":bz2",
    }

    def open(self, name, mode, fmt):
        return tarfile.open(name, mode + self.support_format.get(fmt))

    def type_check(self, obj):
        return isinstance(obj, tarfile.TarFile)

    def file_check(self, file):
        return tarfile.is_tarfile(file)

    def _close(self, obj):
        obj.close()

    def _pack(self, obj, filename):
        obj.add(filename)

    def _extractall(self, obj, extract_path):
        obj.extractall(extract_path)


class ZipCompress(Compress):
    exception = zipfile.error
    support_format = {
        "szip": zipfile.ZIP_STORED,
        "dzip": zipfile.ZIP_DEFLATED,
        "bzip": zipfile.ZIP_BZIP2,
        "lzip": zipfile.ZIP_LZMA,
        "zip": zipfile.ZIP_DEFLATED,
    }

    def open(self, name, mode, fmt):
        name = name.replace(fmt, "zip")
        return zipfile.ZipFile(name, mode, self.support_format.get(fmt))

    def type_check(self, obj):
        return isinstance(obj, zipfile.ZipFile)

    def file_check(self, file):
        return zipfile.is_zipfile(file)

    def _close(self, obj):
        obj.close()

    def _pack(self, obj, filename):
        obj.write(filename)

    def _extractall(self, obj, extract_path):
        obj.extractall(extract_path)


class TarManagerError(Exception):
    pass


class TarManager(object):
    support_formats = set(list(TarCompress.support_format.keys()) + list(ZipCompress.support_format.keys()))

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
        fmt = os.path.splitext(name)[-1][1:]
        return fmt if fmt in TarManager.support_formats else ""

    @staticmethod
    def get_support_format():
        return list(TarManager.support_formats)

    @staticmethod
    def create_compress_object(fmt):
        if fmt in TarCompress.support_format:
            return TarCompress()
        elif fmt in ZipCompress.support_format:
            return ZipCompress()
        else:
            return None

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
            fmt = fmt if fmt in TarManager.get_support_format() else TarManager.get_file_format(name)

            compress = TarManager.create_compress_object(fmt)
            if not isinstance(compress, Compress):
                raise TarManagerError("Unknown package format: {}".format(os.path.basename(name)))

            # Entry package directory
            os.chdir(path)

            # Create package file
            tar_file = compress.open(name, TarManager.operateDict.get("write"), fmt)
            if not compress.type_check(tar_file):
                raise TarManagerError("Create packages error")

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
                        compress.pack(tar_file, full_path)
                        continue

                    # File name is pass the filter
                    if filters and filters(extension_name):
                        compress.pack(tar_file, full_path)
                        continue

                    # No in extensions and not in filters
                    if len(extensions) or filters:
                        continue

                    # Do not has extension and filters pack all
                    compress.pack(tar_file, full_path)

            # Close tarFile
            compress.close(tar_file)

        except OSError as e:
            raise TarManagerError("Change work dir error:{}".format(e))
        except (ZipCompress.exception, TarCompress.exception) as e:
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

            # Get file format
            fmt = fmt if fmt in TarManager.get_support_format() else TarManager.get_file_format(file_path)

            compress = TarManager.create_compress_object(fmt)
            if not isinstance(compress, Compress):
                raise TarManagerError("Unknown package format:{0:s}".format(file_path))

            # Check tar file format
            if not compress.file_check(file_path):
                raise TarManagerError("Package:{0:s} is not a tarfile".format(file_path))

            # Check unpack directory
            if len(unpack_path) == 0:
                unpack_path = os.path.splitext(os.path.basename(file_path))[0]

            if not os.path.isdir(unpack_path):
                os.makedirs(unpack_path)

            # Open as tarfile and extractall and close finally
            tar_file = compress.open(file_path, TarManager.operateDict.get("read"), fmt)
            compress.extractall(tar_file, unpack_path)
            compress.close(tar_file)

        except (IOError, OSError, ZipCompress.exception, TarCompress.exception, shutil.Error) as e:
            raise TarManagerError('Extract failed：IOError, {}'.format(e))

