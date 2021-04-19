# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
from typing import List, Sequence

__all__ = ['get_git_release_date', 'get_git_release_hash', 'get_git_commit_count',
           'get_dir_file_list', 'py2exe_clear_setup', 'py2exe_setup_module', 'py_installer_add_data_dir']


def get_git_commit_count() -> int:
    return int(subprocess.Popen("git rev-list HEAD --count", stdout=subprocess.PIPE).stdout.read().decode())


def get_git_release_hash(short: bool = True) -> str:
    fmt = "%h" if short else "%H"
    return subprocess.Popen("git log -1 --pretty=format:{}".format(fmt),
                            stdout=subprocess.PIPE).stdout.read().decode().strip()


def get_git_release_date(fmt: str = '%Y%m%d%H%M%S') -> str:
    latest_hash = get_git_release_hash(False)
    return subprocess.Popen('git log --pretty=format:"%cd" --date=format:{} {} -1'.format(fmt, latest_hash),
                            stdout=subprocess.PIPE).stdout.read().decode().strip()


def get_dir_file_list(path: str) -> List[str]:
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


def py2exe_setup_module(subdir: str):
    if os.path.isdir(subdir) and os.path.isfile(os.path.join(subdir, "setup.py")):
        cwd = os.getcwd()
        os.chdir(subdir)
        os.system("python setup.py py2exe")
        os.chdir(cwd)


def py2exe_clear_setup(module_list=Sequence[str]):
    # Generate remove file list
    remove_list = ["dist", "build"]
    for subdir in module_list:
        remove_list.append(os.path.join(subdir, "dist"))
        remove_list.append(os.path.join(subdir, "build"))

    # Remove temp file list in remove file list
    for subdir in remove_list:
        if os.path.isdir(subdir):
            shutil.rmtree(subdir)


def py_installer_add_data_dir(data_dir_path: str):
    files = list()
    for file in get_dir_file_list(data_dir_path):
        files.append((file, file, 'DATA'))

    return files
