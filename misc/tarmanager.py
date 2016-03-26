# -*- coding: utf-8 -*-

"""
Tar package file manager, support package file/directory to tar, gz, bz2  or unpackage file
"""


import os
import shutil
import tarfile


__all__ = ['TarManager']


class TarManager(object):
    
    formatDict = {
        
        "tar": ":",
        "gz": ":gz",
        "bz2": ":bz2",
    }
    
    operDict = {
        
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

        if "." not in name:
            return ""

        formats = name.split(".")[-1]
        return formats if formats in TarManager.formatDict.keys() else ""

    @staticmethod
    def get_support_format():
        return TarManager.formatDict.keys()
    
    @staticmethod
    def package(path, name, fmt="", verbose=False):
        """Package directory to a tarfile

        :param path: directory path
        :param name: package name
        :param fmt: package formats
        :param verbose: show verbose message
        :return: success return (True, "")  else (False, error)
        """

        result = (True, "")
        current_path = os.getcwd()
    
        try:
        
            # Make sure path is a dir
            if not os.path.isdir(path):
                result = False, "Path: {0:s} is not a directory".format(path)
                raise

            # Check name
            if not os.path.isdir(os.path.dirname(name)):
                name = os.path.join(current_path, os.path.basename(name))
                
            # Get file format
            if len(fmt) and fmt in TarManager.get_support_format():
                formats = fmt
            else:
                formats = TarManager.get_file_format(name)
           
            if len(formats) == 0:
                result = False, "Unknown package format: {0:s}".format(os.path.basename(name))
                raise
        
            # Entry package directory
            os.chdir(path)
        
            # Create package file
            tar_file = tarfile.open(name, TarManager.operDict.get("write") + TarManager.formatDict.get(formats))
            
            # Print package info
            if verbose:
                print "{0:s} -> {1:s}".format(os.path.abspath(path), name)
        
            # Traversal all files in path add to tarFile
            for root, dirs, files in os.walk('.'):
                for file_name in files:
                    full_path = os.path.join(root, file_name)
                
                    # Verbose message
                    if verbose:
                        print full_path[2:]
                        
                    tar_file.add(full_path)
                
            # Close tarFile
            tar_file.close()
    
        except OSError, e:
            result = False, "Change work dir error:{0:S}".format(e)
        
        except tarfile.TarError, e:
            result = False, "Create tar file error:{0:s}".format(e)
        
        finally:
            os.chdir(current_path)
            return result

    @staticmethod
    def unpackage(file_path, unpackage_path="", fmt=""):
        """Unpackage file_path specified file to unpacakge_path

        :return:
        :param file_path: Tar file path
        :param unpackage_path: Unpackage path
        :param fmt: package format
        :return: result, error
        """

        result = (True, "")
    
        try:
        
            # Check tar file path
            if not os.path.isfile(file_path):
                result = False, "Tar file: {0:s} is not exist".format(file_path)
                raise
        
            # Check tar file format
            if not tarfile.is_tarfile(file_path):
                result = False, "Package:{0:s} is not a tarfile".format(file_path)
                raise

            if len(fmt) and fmt in TarManager.get_support_format():
                formats = fmt
            else:
                formats = TarManager.get_file_format(file_path)

            if len(formats) == 0:
                result = False, "Unknown package format:{0:s}".format(file_path)
                raise
        
            # Check unpackage directory
            if len(unpackage_path) == 0:
                unpackage_path = os.path.basename(file_path.split(".")[0])

            if not os.path.isdir(unpackage_path):
                os.makedirs(unpackage_path)
            
            # Open as tarfile and extractall and close finally
            tar_file = tarfile.open(file_path, TarManager.operDict.get("read") + TarManager.formatDict.get(formats))
            tar_file.extractall(unpackage_path)
            tar_file.close()
    
        except IOError, e:
        
            result = False, 'Extract failed：IOError, {0:s}'.format(e)
            
        except OSError, e:
        
            result = False, 'Extract failed：OSError, {0:s}'.format(e)
        
        except tarfile.TarError, e:
            
            result = False, 'Extract failed：TarError, {0:s}'.format(e)

        except shutil.Error, e:
        
            result = False, 'Extract failed：Shutil.Error, {0:s}'.format(e)
    
        finally:
            
            return result
