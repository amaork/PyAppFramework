# -*- coding: utf-8 -*-

from ..misc.setup import get_git_commit_count, get_git_release_hash, get_git_release_date


if __name__ == "__main__":
    print "Commit count:{0:d}".format(get_git_commit_count())
    print "Release hash:{0:s}".format(get_git_release_hash())
    print "Release data:{0:s}".format(get_git_release_date())
