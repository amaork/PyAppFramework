# -*- coding: utf-8 -*-
import os
import re
import ftplib
from typing import Optional, Callable, List, Sequence
__all__ = ['FTPClient', 'FTPClientError']


class FTPClientError(Exception):
    pass


class FTPClient(object):
    ROOT = "/"
    EXTx_FS_RECOVERY_DIR = "lost+found"

    def __init__(self, address: str, port: int = 21,
                 username: str = "anonymous", password: str = "anonymous@", timeout: int = 30, verbose: bool = False):
        """FTP client base ftplib, support recursive download, upload, delete whole directory

        :param address: FTP Server address
        :param port: FTP Server port
        :param username: Username default is anonymous
        :param password: Username password
        :param timeout: timeout
        :param verbose: output verbose message
        :return:
        """
        self.port = port
        self.address = address
        self.verbose = verbose
        self.timeout = timeout
        self.password = password
        self.username = username
        self.ftp = self.create_new_connection()

    def __del__(self):
        try:
            self.ftp.close()
        except AttributeError:
            pass

    @staticmethod
    def dirname(path: str) -> str:
        origin = os.path.dirname(path)
        return origin.replace("\\", "/")

    @staticmethod
    def join(path: str, *paths) -> str:
        org = os.path.join(path, *paths)
        return org.replace("\\", "/")

    @staticmethod
    def root_join(*paths) -> str:
        return FTPClient.join(FTPClient.ROOT, *paths)

    def relative_join(self, *path) -> str:
        return self.join(self.ftp.pwd(), *path)

    def create_new_connection(self) -> ftplib.FTP:
        """Create a ftp object and connect to server

        :return:
        """

        # Create a ftp object
        ftp = ftplib.FTP()
        
        try:
            # Connect ftp server
            ftp.connect(host=self.address, port=self.port, timeout=self.timeout)
            ftp.login(self.username, self.password)
        except ftplib.all_errors as e:
            raise FTPClientError("FTP connect to:{} error:{}".format(self.address, e))
        
        return ftp
        
    def is_dir(self, name: str) -> bool:
        """Check if name specified path is a directory

        :param name: path name
        :return: return true if path name is a directory
        """
        try:

            cwd = self.ftp.pwd()
            # Try to enter directory
            self.ftp.cwd(name)

            # Success, entered, then return
            self.ftp.cwd(cwd)
            return True

        # Enter failed, is not a directory
        except ftplib.all_errors:
            return False

    def is_file(self, name: str) -> bool:
        """Check if name specified path is a normal file

        :param name: path name
        :return: return true if path name is a file
        """

        if name not in self.ftp.nlst("."):
            return False
        
        return not self.is_dir(name)

    def is_exist(self, path: str) -> bool:
        """Check if path is existed

        :param path: absolute path
        :return: True if path exist False not exist
        """
        return os.path.basename(path) in self.get_file_list(self.dirname(path))

    def is_file_abs(self, path: str) -> bool:
        """Check if path is a file

        :param path: absolute path
        :return: True if path is a file, False means not exist or is a directory
        """
        if not self.is_exist(path):
            return False

        return not self.is_dir(path)

    def create_dirs(self, path: str) -> bool:
        """Recursive Create a directory at ftp server

        :param path: path
        :return: success return true else false
        """

        path_list = path.split("/")[1:]

        # Already exist return
        if self.is_dir(path):
            return True
                
        try:

            for i in range(len(path_list)):
                dir_name = ""
                for j in range(i + 1):
                    dir_name = self.join(dir_name, path_list[j])

                if not self.is_dir(dir_name):
                    self.ftp.mkd(dir_name)
                    
        except ftplib.all_errors as e:
            print("Recursive create dirs:{} error:{}".format(path, e))
            return False
            
        return True
           
    def get_file_list(self, path: str) -> List[str]:
        """Get specified path file list

        :param path:
        :return: file list
        """

        lst = []
        
        try:
            
            # Create a ftp client
            ftp = self.create_new_connection()
            
            # Make sure path is a dir
            ftp.cwd(path)
            
            # Get dir file  list
            lst = ftp.nlst(".")

        except ftplib.all_errors as e:
            print("Get dir:{} file list error:{}".format(path, e))
        
        return lst
        
    def download_dir(self, remote_dir: str, local_dir: str,
                     exclude: Optional[Sequence[str]] = None,
                     callback: Optional[Callable[[str], None]] = None):
        """Recursive download remote directory data to local dir without remote dir name equal cp remoteDir/* localDir/

        :param remote_dir: remote directory path
        :param local_dir: local directory path
        :param exclude: exclude list file in exclude list do not download, support file extensions such as *.bmp
        :param callback: callback before download file
        """

        pwd = ""
        exclude = exclude if isinstance(exclude, (list, tuple)) else list()
        extensions = [x[2:] for x in [name for name in exclude if re.search(r"\*.(.*?)", name, re.S)]]
               
        try:
            # If local dir is not exist create it
            if not os.path.isdir(local_dir):
                os.makedirs(local_dir)
        
            # Enter remote dir
            pwd = self.ftp.pwd()
            self.ftp.cwd(remote_dir)
        
            # Recursive download all files
            for file_name in self.ftp.nlst("."):
                extension_name = file_name.split(".")[-1]

                # Ignored
                if file_name in exclude or extension_name in extensions:
                    continue
                
                # file is a directory recursive call self download all
                if self.is_dir(file_name):
                    self.download_dir(file_name, os.path.join(local_dir, file_name), exclude, callback)
                # Normal file call download file
                else:
                    remote_file = self.join(self.ftp.pwd(), file_name)
                    if callback and hasattr(callback, "__call__"):
                        callback(remote_file)
                    self.download_file(remote_file, local_dir)
                    if callback and hasattr(callback, "__call__"):
                        callback(os.path.join(local_dir, file_name))

        except ftplib.error_perm as e:
            raise FTPClientError("Download error remote dir:{} is not exist:{}".format(remote_dir, e))
        except OSError as e:
            raise FTPClientError("Download error create local dir:{} error:{}".format(local_dir, e))
        finally:
            if len(pwd):
                self.ftp.cwd(pwd)
                      
    def download_file(self, remote_path: str, local_path: str, local_name: str = ''):
        """Download a file to local directory save as local_name

        :param remote_path: FTP Server file path
        :param local_path: download file path
        :param local_name: local save as file name
        """

        try:
            
            # Check local path
            if os.path.isfile(local_path):
                raise FTPClientError("Download error local path:{} is not a directory".format(local_path))
        
            if not os.path.isdir(local_path):
                os.makedirs(local_path)
        
            # Check download path
            if local_path[-1] != os.sep:
                local_path += os.sep
            
            # Create a ftp client object
            ftp = self.create_new_connection()
            
            # Download file
            file_name = os.path.basename(local_name if local_name else remote_path)
            with open(os.path.join(local_path, file_name), 'wb') as fp:
                ftp.retrbinary('RETR ' + remote_path, fp.write)

            if self.verbose:
                print("Downloading:{}".format(remote_path))
        except ftplib.all_errors as e:
            raise FTPClientError("Download file:{} error:{}".format(remote_path, e))
        except AttributeError as e:
            raise FTPClientError("Download file:{} error:{}".format(remote_path, e))

    def upload_dir(self, local_dir: str, remote_dir: str,
                   exclude: Optional[Sequence[str]] = None,
                   callback=Optional[Callable[[str], None]]):
        """Recursive upload local dir to remote, if remote dir is not exist create it, else replace all files

        :param local_dir: Local path, will upload
        :param remote_dir: FTP Server remote path, receive upload data
        :param exclude: exclude list file in exclude list do not upload, support file extensions such as *.bmp
        :param callback: callback before upload file
        """

        pwd = ""
        exclude = exclude if isinstance(exclude, (list, tuple)) else list()
        extensions = [x[2:] for x in [name for name in exclude if re.search(r"\*.(.*?)", name, re.S)]]
        
        try:
            
            # Check local dir
            if not os.path.isdir(local_dir):
                raise FTPClientError("Upload dir error local dir:{} is not exist".format(local_dir))
                 
            # Check remote dir
            if self.is_file(remote_dir):
                raise FTPClientError("Upload dir error remote dir:{} is not a directory".format(remote_dir))
        
            # Enter local dir
            pwd = os.getcwd()
            os.chdir(local_dir)
                
            # Recursive upload local file
            for file_name in os.listdir('.'):
                extension_name = file_name.split(".")[-1]

                if file_name in exclude or extension_name in extensions:
                    continue
                                
                # Is a directory, recursive call self upload all
                if os.path.isdir(os.path.abspath(file_name)):
                    self.upload_dir(file_name, self.join(remote_dir, file_name), exclude, callback)
                else:
                    if callback and hasattr(callback, "__call__"):
                        callback(os.path.join(pwd, local_dir, file_name))
                    # Upload to remote dir same directory
                    self.upload_file(file_name, remote_dir)

        except (IOError, ftplib.error_perm) as e:
            raise FTPClientError("Uploading:{} error:{}".format(os.getcwd(), e))
        finally:
            if len(pwd):
                os.chdir(pwd)

    def upload_file(self, local_path: str, remote_path: str, remote_name: str = ""):
        """Upload local_path specified file to remote path

        :param local_path: Local file path
        :param remote_path: Remote path
        :param remote_name: If is not empty will rename to this name
        """

        pwd = ""
        
        try:
            
            # Local path check
            if not os.path.isfile(local_path):
                raise FTPClientError("Upload error, local file:{} doesn't exist".format(local_path))

            # Remote path check, if remote path isn't a dir create it
            if not self.is_dir(remote_path) and not self.create_dirs(remote_path):
                raise FTPClientError("Upload error, remote path:{} is not a directory".format(remote_path))
            
            # Enter remote path
            pwd = self.ftp.pwd()
            self.ftp.cwd(remote_path)
            
            # Upload file to remote
            if len(remote_name):
                self.ftp.storbinary('STOR ' + os.path.basename(remote_name), open(local_path, 'rb'))
            else:
                self.ftp.storbinary('STOR ' + os.path.basename(local_path), open(local_path, 'rb'))
            
            if self.verbose:
                print("Uploading:{}".format(os.path.abspath(local_path)))
                
        except ftplib.all_errors as e:
            raise FTPClientError("Upload file:{} error:{}".format(os.path.basename(local_path), e))
        finally:
            if len(pwd):
                self.ftp.cwd(pwd)
             
    def remove_files(self, remote_dir: str, remove_files: List[str],
                     callback: Optional[Callable[[str], None]] = None):
        """Remove files form remote dir

        :param remote_dir: Remote dir
        :param remove_files: Will remove files list
        :param callback: callback before upload file
        """
        pwd = ""

        try:
            
            # Check remote dir
            if not self.is_dir(remote_dir):
                raise FTPClientError("Remove files error, remote dir:{} is not exist".format(remote_dir))

            # Automatic ignore extX filesystem recovery dir
            if self.EXTx_FS_RECOVERY_DIR in remove_files:
                remove_files.remove(self.EXTx_FS_RECOVERY_DIR)
            
            # Enter remote dir
            pwd = self.ftp.pwd()
            self.ftp.cwd(remote_dir)

            # Recursive delete all files
            for file_name in remove_files:
                
                remote_path = self.join(remote_dir, file_name)

                # file is a directory
                if self.is_dir(remote_path):
                    # Directory is empty, just remove it
                    if len(self.get_file_list(remote_path)) == 0:
                        self.ftp.rmd(remote_path)
                        continue

                    # Remove dir file first then remove dir itself
                    self.remove_dir(remote_path)
                # file is normal file
                elif self.is_file(file_name):
                    if self.verbose:
                        print("Deleting:{}".format(remote_path))

                    if callback and hasattr(callback, "__call__"):
                        callback(remote_path)
                    self.ftp.delete(file_name)
                else:
                    print("Path:{} not exist, jump".format(remote_path))

        except ftplib.all_errors as e:
            raise FTPClientError("Remove files from:{}, error:{}".format(remote_dir, e))
        finally:
            if len(pwd):
                self.ftp.cwd(pwd)
                
    def remove_dir(self, remote_dir: str):
        """Recursive delete remote dir all files

        :param remote_dir: Remote dir will delete all files
        :return: result, error
        """
        self.remove_files(remote_dir, self.get_file_list(remote_dir))

        try:
            self.ftp.rmd(remote_dir)
        except ftplib.all_errors as e:
            raise FTPClientError("Remove dir:{} error:{}".format(remote_dir, e))

    def force_remove_dir(self, remote_dir: str):
        try:
            # Try to remove the whole dir
            self.remove_dir(remote_dir)
        except FTPClientError:
            try:
                # Failed remove all files in this directory and ignore errors
                self.remove_files(remote_dir, self.get_file_list(remote_dir))
            except FTPClientError:
                pass

    def force_remote_file(self, file: str):
        try:
            if self.is_file_abs(file):
                self.remove_files(self.dirname(file), [os.path.basename(file)])
        except FTPClientError:
            pass
