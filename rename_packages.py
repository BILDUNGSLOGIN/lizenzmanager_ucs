#!/usr/bin/env python

import datetime
import os
import re
import time


def rename_packages():
    regex_find = re.compile('.*_all.deb')
    regex = re.compile('_all.deb')
    now = datetime.datetime.now()

    files = []

    for (dirpath, dirnames, filenames) in os.walk('./'):
        for filename in filenames:
            if regex_find.match(filename):
                files.append(filename)
        break

    for filename in files:
        os.rename(filename,
                  regex.sub('A~' + str(int(time.mktime(now.timetuple()))) + '_all.deb', filename))


if __name__ == '__main__':
    rename_packages()
