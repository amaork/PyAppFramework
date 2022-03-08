# -*- coding: utf-8 -*-
"""
Tar package file manager, support package file/directory to tar, gz, bz2  or un-package file
"""
import os
import shutil
import tarfile
import zipfile
import lz4.frame
from typing import Optional, Callable, List, Sequence, Tuple, Union
__all__ = ['TarManager', 'TarManagerError', 'TarManagerCallback']

# callback(processingFilename, processingFileIndex)
TarManagerCallback = Callable[[str, int], None]
TarManagerFilterCallback = Callable[[str], bool]


class Compress(object):
    exception = Exception
    support_format = {}

    def __init__(self, simulate: bool = False, callback: Optional[TarManagerCallback] = None):
        self._processing = 0
        self._simulate = simulate
        self._callback = callback

    def open(self, name: str, mode: str, fmt: str):
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

    def get_members(self, obj) -> List[str]:
        pass

    def callback(self, name: str):
        self._processing += 1

        if hasattr(self._callback, "__call__"):
            self._callback(name, self._processing)

    def _pack(self, obj, filename: str):
        pass

    def pack(self, obj, filename: str):
        if not self.type_check(obj) or not os.path.isfile(filename):
            return

        if self._simulate:
            self.callback(filename)
        else:
            self.callback(filename)
            self._pack(obj, filename)

    def _extract(self, obj, filename: str, extract_path: str):
        pass

    def extract(self, obj, filename: str, extract_path: str):
        if not self.type_check(obj) or not os.path.isdir(extract_path):
            return

        if self._simulate:
            self.callback(filename)
        else:
            self.callback(filename)
            self._extract(obj, filename, extract_path)

    def _extractall(self, obj, extract_path: str):
        pass

    def extractall(self, obj, extract_path: str):
        if not self.type_check(obj):
            return

        if self._simulate:
            self.callback(extract_path)
        else:
            self.callback(extract_path)
            self._extractall(obj, extract_path)


class TarCompress(Compress):
    exception = tarfile.TarError
    TarObject = tarfile.TarFile
    support_format = {
        "tar": ":",
        "gz": ":gz",
        "tgz": ":gz",
        "bz2": ":bz2",
        "tbz2": ":bz2",
    }

    def open(self, name: str, mode: str, fmt: str) -> TarObject:
        return tarfile.open(name, mode + self.support_format.get(fmt))

    def type_check(self, obj: TarObject):
        return isinstance(obj, tarfile.TarFile)

    def file_check(self, file: str):
        return tarfile.is_tarfile(file)

    def _close(self, obj: TarObject):
        obj.close()

    def get_members(self, obj: TarObject) -> List[str]:
        return obj.getnames()

    def _pack(self, obj: TarObject, filename: str):
        obj.add(filename)

    def _extractall(self, obj: TarObject, extract_path: str):
        obj.extractall(extract_path)

    def _extract(self, obj: TarObject, filename: str, extract_path: str):
        obj.extract(filename, extract_path)


class ZipCompress(Compress):
    exception = zipfile.error
    ZipObject = zipfile.ZipFile
    support_format = {
        "szip": zipfile.ZIP_STORED,
        "dzip": zipfile.ZIP_DEFLATED,
        "bzip": zipfile.ZIP_BZIP2,
        "lzip": zipfile.ZIP_LZMA,
        "zip": zipfile.ZIP_DEFLATED,
    }

    def open(self, name: str, mode: str, fmt: str) -> ZipObject:
        name = name.replace(fmt, "zip")
        return zipfile.ZipFile(name, mode, self.support_format.get(fmt))

    def type_check(self, obj: ZipObject):
        return isinstance(obj, zipfile.ZipFile)

    def file_check(self, file):
        return zipfile.is_zipfile(file)

    def _close(self, obj: ZipObject):
        obj.close()

    def get_members(self, obj: ZipObject) -> List[str]:
        return obj.namelist()

    def _pack(self, obj: ZipObject, filename: str):
        obj.write(filename)

    def _extractall(self, obj: ZipObject, extract_path: str):
        obj.extractall(extract_path)

    def _extract(self, obj: ZipObject, filename: str, extract_path: str):
        obj.extract(filename, extract_path)


class Lz4Compress(TarCompress):
    support_format = {
        'lz4': ':'
    }
    Lz4Object = TarCompress.TarObject

    @staticmethod
    def __get_lz4_filename(filename: str) -> str:
        return filename + '.lz4'

    @staticmethod
    def __get_org_filename(filename: str) -> str:
        return os.path.splitext(filename)[0] if '.lz4' in filename else filename

    def open(self, name: str, mode: str, fmt: str) -> Lz4Object:
        return tarfile.open(name, mode + self.support_format.get(fmt))

    def _pack(self, obj: Lz4Object, filename: str):
        # Read original file
        with open(filename, 'rb') as read_fp:
            input_data = read_fp.read()

        # Compress to lz4
        lz4_file = self.__get_lz4_filename(filename)
        with open(lz4_file, 'wb') as write_fp:
            write_fp.write(lz4.frame.compress(input_data))

        try:
            # Add lz4 to tar
            obj.add(lz4_file)
        finally:
            if os.path.isfile(lz4_file):
                os.unlink(lz4_file)

    def _extractall(self, obj: Lz4Object, extract_path: str):
        obj.extractall(extract_path)

        for filename in os.listdir(extract_path):
            lz4_file_path = os.path.join(extract_path, filename)

            try:
                with open(os.path.join(extract_path, self.__get_org_filename(filename)), 'wb') as write_fp:
                    with open(lz4_file_path, 'rb') as read_fp:
                        write_fp.write(lz4.frame.decompress(read_fp.read()))
            finally:
                if os.path.isfile(lz4_file_path):
                    os.unlink(lz4_file_path)

    def _extract(self, obj: Lz4Object, filename: str, extract_path: str):
        obj.extract(filename, extract_path)
        lz4_file_path = os.path.join(extract_path, filename)

        try:
            with open(os.path.join(extract_path, self.__get_org_filename(filename)), 'wb') as write_fp:
                with open(lz4_file_path, 'rb') as read_fp:
                    write_fp.write(lz4.frame.decompress(read_fp.read()))
        finally:
            if os.path.isfile(lz4_file_path):
                os.unlink(lz4_file_path)


class TarManagerError(Exception):
    pass


class TarManager(object):
    support_formats = set(
        list(TarCompress.support_format.keys()) +
        list(ZipCompress.support_format.keys()) +
        list(Lz4Compress.support_format.keys())
    )

    operateDict = {
        "read": "r",
        "write": "w",
    }

    @staticmethod
    def get_file_format(name: str) -> str:
        """Get file format

        :param name: file name
        :return: file format
        """

        name = os.path.basename(name)
        fmt = os.path.splitext(name)[-1][1:]
        return fmt if fmt in TarManager.support_formats else ""

    @staticmethod
    def get_support_format() -> List[str]:
        return list(TarManager.support_formats)

    @staticmethod
    def create_compress_object(fmt: str, simulate: bool = False,
                               callback: Optional[TarManagerCallback] = None) -> Union[Compress, None]:
        if fmt in TarCompress.support_format:
            return TarCompress(simulate, callback)
        elif fmt in ZipCompress.support_format:
            return ZipCompress(simulate, callback)
        elif fmt in Lz4Compress.support_format:
            return Lz4Compress(simulate, callback)
        else:
            return None

    @staticmethod
    def check_and_open_compress_object(
            file_path: str, fmt: Optional[str] = None,
            simulate: bool = False, callback: Optional[TarManagerCallback] = None) -> Tuple[Compress, object]:
        # Check tar file path
        if not os.path.isfile(file_path):
            raise TarManagerError("Tarfile: {0:s} is not exist".format(file_path))

        # Get file format
        fmt = fmt if fmt in TarManager.get_support_format() else TarManager.get_file_format(file_path)

        compress = TarManager.create_compress_object(fmt, simulate=simulate, callback=callback)
        if not isinstance(compress, Compress):
            raise TarManagerError("Unknown package format:{0:s}".format(file_path))

        # Check tar file format
        if not compress.file_check(file_path):
            raise TarManagerError("Package:{0:s} is not a tarfile".format(file_path))

        return compress, compress.open(file_path, TarManager.operateDict.get("read"), fmt)

    @staticmethod
    def pack(path: str, name: str, fmt: Optional[str] = None,
             extensions: Optional[Sequence[str]] = None, filters: Optional[TarManagerFilterCallback] = None,
             verbose: bool = False, simulate: bool = False, callback: Optional[TarManagerCallback] = None):
        """Package directory to a tarfile

        :param path: directory path
        :param name: package name
        :param fmt: package formats
        :param extensions: if set only pack those extension names
        :param filters: if set when filter is true will be packed
        :param verbose: show verbose message
        :param simulate: set simulate means not real pack only run process to get how many files it;s need to pack
        :param callback: before pack every file will call this callback function
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

            compress = TarManager.create_compress_object(fmt, simulate, callback)
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

                    # Do not have extension and filters pack all
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
    def unpack(file_path: str, unpack_path: str = "", fmt: Optional[str] = None,
               simulate: bool = False, callback: Optional[TarManagerCallback] = None):
        """Unpack file_path specified file to unpack_path

        :return:
        :param file_path: Tar file path
        :param unpack_path: Unpack path
        :param fmt: package format
        :param simulate: set simulate means not real unpack only run process to get how many files it;s need to unpack
        :param callback: before unpack every file will call this callback function
        """
        try:
            # Check unpack directory
            if len(unpack_path) == 0:
                unpack_path = os.path.splitext(os.path.basename(file_path))[0]

            if not os.path.isdir(unpack_path):
                os.makedirs(unpack_path)

            # Open as tarfile and extractall and close finally
            compress, tar_file = TarManager.check_and_open_compress_object(file_path, fmt, simulate, callback)
            for member in compress.get_members(tar_file):
                compress.extract(tar_file, member, unpack_path)
            compress.close(tar_file)
        except (IOError, OSError, ZipCompress.exception, TarCompress.exception, shutil.Error) as e:
            raise TarManagerError('Extract failed：IOError, {}'.format(e))

    @staticmethod
    def get_members(file_path: str, fmt: Optional[str] = None) -> List[str]:
        try:
            compress, tar_file = TarManager.check_and_open_compress_object(file_path, fmt)
            return compress.get_members(tar_file)
        except (IOError, OSError, ZipCompress.exception, TarCompress.exception, shutil.Error) as e:
            raise TarManagerError("Get file members error, {}".format(e))
