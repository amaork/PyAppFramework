# -*- coding: utf-8 -*-

import os
import shutil


__all__ = ['get_git_release_date', 'get_git_release_hash', 'get_git_commit_count',
           'get_dir_file_list', 'py2exe_clear_setup', 'py2exe_setup_module']


def get_git_commit_count():
    return int(os.popen("git log --pretty=format:'' | wc -l", 'r').read())


def get_git_release_hash():
    return os.popen("git log -1 --pretty=format:%h").read().strip()


def get_git_release_date():
    return os.popen("git log -1 --pretty=format:'%ad' --date=iso | "
                    "tr -d - | tr -d : | tr ' ' '-' | cut -c 3-15").read().strip()


def get_dir_file_list(path):
    """Get directory all file lists

    :param path:
    :return:
    """
    lst = list()

    if os.path.isdir(path):
        for filename in os.listdir(path):
            if filename.endswith(".py") or filename.endswith(".pyc"):
                continue

            full_path = os.path.join(path, filename)

            if os.path.isdir(full_path):
                lst.extend(get_dir_file_list(full_path))
            else:
                lst.append(full_path)

    return lst


def py2exe_setup_module(subdir):
    if os.path.isdir(subdir) and os.path.isfile(os.path.join(subdir, "setup.py")):
        cwd = os.getcwd()
        print "++++++++++++++++++++++++++++++++++++++++++++", os.getcwd()
        os.chdir(subdir)
        print "--------------------------------------------", os.getcwd()
        os.system("python setup.py py2exe")
        os.chdir(cwd)
        print "============================================", os.getcwd()


def py2exe_clear_setup(module_list=[]):
    # Generate remove file list
    remove_list = ["dist", "build"]
    for subdir in module_list:
        remove_list.append(os.path.join(subdir, "dist"))
        remove_list.append(os.path.join(subdir, "build"))

    # Remove temp file list in remove file list
    for subdir in remove_list:
        if os.path.isdir(subdir):
            shutil.rmtree(subdir)
