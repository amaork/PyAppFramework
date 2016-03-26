# -*- coding: utf-8 -*-

"""
FTP client base ftplib,  support recursive download, upload, delete directory and normal files.
"""

import os
import ftplib


__all__ = ['FTPClient']


class FTPClient(object):
    def __init__(self, addr, port=21, username="anonymous", password="anonymous@", timeout=30, verbose=False):
        """FTP client base ftplib, support recursive download, upload, delete whole directory

        :param addr: FTP Server address
        :param port: FTP Server port
        :param username: Username default is anonymous
        :param password: Username password
        :param timeout: timeout
        :param verbose: output verbose message
        :return:
        """
        self.addr = addr
        self.port = port
        self.verbose = verbose
        self.timeout = timeout
        self.password = password
        self.username = username
        self.ftp = self.create_new_connection()

    def __del__(self):
        self.ftp.close()
        
    def create_new_connection(self):
        """Create a ftp object and connect to server

        :return:
        """

        # Create a ftp object
        ftp = ftplib.FTP()
        
        try:

            # Connect ftp server
            ftp.connect(host=self.addr, port=self.port, timeout=self.timeout)
            ftp.login(self.username, self.password)

        except ftplib.all_errors, e:
            print "FTP connect to:{0:s} error:{1:s}".format(self.addr, e)
        
        return ftp
        
    def is_dir(self, name):
        """Check if name specified path is a directory

        :param name: path name
        :return: return true if path name is a directory
        """
        try:
                        
            # Change dir if not error is means an dir
            self.ftp.cwd(name)

            self.ftp.cwd("../")

            return True
            
        except ftplib.all_errors:
            
            return False
              
    def is_file(self, name):
        """Check if name specified path is a normal file

        :param name: path name
        :return: return true if path name is a file
        """

        if name not in self.ftp.nlst("."):
            return False
        
        return not self.is_dir(name)
    
    def create_dirs(self, path):
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
                    dir_name = dir_name + "/" + path_list[j]
                
                if not self.is_dir(dir_name):
                    self.ftp.mkd(dir_name)
                    
        except ftplib.all_errors, e:
            
            print "Recursive create dirs:{0:s} error:{1:s}".format(path, e)
            return False
            
        return True
           
    def get_file_list(self, path):
        """Get specified path file list

        :param path:
        :return: file list
        """

        flist = []
        
        try:
            
            # Create a ftp client
            ftp = self.create_new_connection()
            
            # Make sure path is a dir
            ftp.cwd(path)
            
            # Get dir flist list
            flist = ftp.nlst(".")

        except ftplib.all_errors, e:
            print "Get dir:{0:s} file list error:{1:s}".format(path, e)
        
        return flist
        
    def download_dir(self, remote_dir, local_dir):
        """Recursive download remote directory data to local dir without remote dir name equal cp remoteDir/* localDir/

        :param remote_dir: remote directory path
        :param local_dir: local directory path
        :return:
        """

        pwd = ""
               
        try:
            
            # If local dir is not exist create it
            if not os.path.isdir(local_dir):
                os.makedirs(local_dir)
        
            # Enter remote dir
            pwd = self.ftp.pwd()
            self.ftp.cwd(remote_dir)
        
            # Recursive download all files
            for fileName in self.ftp.nlst("."):
                
                # file is a directory
                if self.is_dir(fileName):

                    # Recursive call self download all
                    result = self.download_dir(fileName, os.path.join(local_dir, fileName))
                    if not result[0]:
                        return result
                # Normal file call download file
                else:
                    
                    result = self.download_file(self.ftp.pwd() + '/' + fileName, local_dir)
                    if not result[0]:
                        return result
                    
            # Success
            return True, "Success"
                                      
        except ftplib.error_perm, e:
            return False, "Download error remote dir:{0:s} is not exist:{1:s}".format(remote_dir, e)

        except OSError, e:
            return False, "Download error create local dir:{0:s} error:{1:s}".format(local_dir, e)
            
        finally:
            if len(pwd):
                self.ftp.cwd(pwd)
                      
    def download_file(self, remote_path, local_path, local_name=''):
        """Download a file to local directory save as local_name

        :param remote_path: FTP Server file path
        :param local_path: download file path
        :param local_name: local save as file name
        :return: true or false
        """

        try:
            
            # Check local path
            if os.path.isfile(local_path):
                return False, "Download error local path:{0:s} is not a directory".format(local_path)
        
            if not os.path.isdir(local_path):
                os.makedirs(local_path)
        
            # Check download path
            if local_path[-1] != os.sep:
                local_path += os.sep
            
            # Create a ftp client object
            ftp = self.create_new_connection()
            
            # Download file
            if len(local_name):
                ftp.retrbinary('RETR ' + remote_path, open(local_path + os.path.basename(local_name), 'wb').write)
            else:
                ftp.retrbinary('RETR ' + remote_path, open(local_path + os.path.basename(remote_path), 'wb').write)
                
            if self.verbose:
                print "Downloading:{0:s}".format(remote_path)

        except ftplib.all_errors, e:
            return False, "Download file:{0:s} error:{1:s}".format(remote_path, e)
        
        except AttributeError, e:
            return False, "Download file:{0:s} error:{1:s}".format(remote_path, e)

        return True, "Success"
           
    def upload_dir(self, local_dir, remote_dir):
        """Recursive upload local dir to remote, if remote dir is not exist create it, else replace all files

        :param local_dir: Local path, will upload
        :param remote_dir: FTP Server remote path, receive upload data
        :return:
        """

        pwd = ""
        
        try:
            
            # Check local dir
            if not os.path.isdir(local_dir):
                return False, "Upload dir error local dir:{0:s} is not exist".format(local_dir)
                 
            # Check remote dir
            if self.is_file(remote_dir):
                return False, "Upload dir error remote dir:{0:s} is not a directory".format(remote_dir)
        
            # Enter local dir
            pwd = os.getcwd()
            os.chdir(local_dir)
                
            # Recursive upload local file
            for fileName in os.listdir('.'):
                                
                # fileName is a directory
                if os.path.isdir(os.path.abspath(fileName)):
                                                             
                    # Recursive Call self upload all
                    result = self.upload_dir(fileName, remote_dir + "/" + fileName)
                    if not result[0]:
                        return result
                
                # fileName is a normal file
                else:
                    
                    # Upload to remote dir same directory
                    result = self.upload_file(fileName, remote_dir)
                    if not result[0]:
                        return result
            
            # Success
            return True, "Success"
                    
        except (IOError, ftplib.error_perm), e:
            return False, "Uploading:{0:s} error:{1:s}".format(os.getcwd(), e)

        finally:
            if len(pwd):
                os.chdir(pwd)
            
    def upload_file(self, local_path, remote_path, remote_name=""):
        """Upload local_path specified file to remote path

        :param local_path: Local file path
        :param remote_path: Remote path
        :param remote_name: If is not empty will rename to this name
        :return: true or false
        """

        pwd = ""
        
        try:
            
            # Local path check
            if not os.path.isfile(local_path):
                return False, "Upload error, local file:{0:s} doesn't exist".format(local_path)

            # Remote path check, if remote path isn't a dir create it
            if not self.is_dir(remote_path) and not self.create_dirs(remote_path):
                return False, "Upload error, remote path:{0:s} is not a directory".format(remote_path)
            
            # Enter remote path
            pwd = self.ftp.pwd()
            self.ftp.cwd(remote_path)
            
            # Upload file to remote
            if len(remote_name):
                self.ftp.storbinary('STOR ' + os.path.basename(remote_name), open(local_path, 'rb'))
            else:
                self.ftp.storbinary('STOR ' + os.path.basename(local_path), open(local_path, 'rb'))
            
            if self.verbose:
                print "Uploading:{0:s}".format(os.path.abspath(local_path))
                
            return True, "Success"
            
        except ftplib.all_errors, e:
            return False, "Upload file:{0:s} error:{1:s}".format(os.path.basename(local_path), e)
        
        finally:
            if len(pwd):
                self.ftp.cwd(pwd)
             
    def remove_files(self, remote_dir, remove_files):
        """Remove files form remote dir

        :param remote_dir: Remote dir
        :param remove_files: Will remove files list
        :return: result, error
        """

        pwd = ""

        # Type check
        if not isinstance(remote_dir, str) or not isinstance(remove_files, list):
            return False, "Param type check error:{0:s},{1:s}".format(type(remote_dir), type(remove_files))

        try:
            
            # Check remote dir
            if not self.is_dir(remote_dir):
                return False, "Remove files error, remote dir:{0:s} is not exist".format(remote_dir)
            
            # Enter remote dir
            pwd = self.ftp.pwd()
            print remote_dir, remove_files, pwd
            self.ftp.cwd(remote_dir)

            # Recursive delete all files
            for fileName in remove_files:
                
                remote_path = remote_dir + "/" + fileName

                # file is a directory
                if self.is_dir(remote_path):

                    # Directory is empty, just remove it
                    if len(self.get_file_list(remote_path)) == 0:
                        print self.ftp.pwd()
                        self.ftp.rmd(remote_path)
                        continue

                    # Remove dir file first then remove dir itself
                    result = self.remove_dir(remote_path)
                    if not result[0]:
                        return result

                # file is normal file
                elif self.is_file(fileName):
                    self.ftp.delete(fileName)
                    
                    if self.verbose:
                        print "Deleting:{0:s}".format(remote_path)

                else:
                    print "Path:{0:s} not exist, jump".format(remote_path)

        except ftplib.all_errors, e:
            return False, "Remove files from:{0:s}, error:{1:s}".format(remote_dir, e)
        
        finally:
            if len(pwd):
                self.ftp.cwd(pwd)
                
        return True, "Success"
        
    def remove_dir(self, remote_dir):
        """Recursive delete remote dir all files

        :param remote_dir: Remote dir will delete all files
        :return: result, error
        """

        result = self.remove_files(remote_dir, self.get_file_list(remote_dir))
        if not result[0]:
            return result
        
        try:
            self.ftp.rmd(remote_dir)
            
        except ftplib.all_errors, e:
            return False, "Remove dir:{0:s} error:{1:s}".format(remote_dir, e)
        
        return True, "Success"
