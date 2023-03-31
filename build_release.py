#!/usr/bin/env python
import datetime
import hashlib
import os


def get_release_header():
    now = datetime.datetime.now()

    return """\
Codename: ucs_4.4-0-bildungslogin/all
Date: {}
Label: Bildungslogin
Origin: VBM Service GmbH
Suite: apt
Version: 4.4.0""".format(now.ctime())


def get_hash_of_file(filename):
    with open(filename) as f:
        output = f.read()
    return hashlib.md5(output).hexdigest(), hashlib.sha1(output).hexdigest(), hashlib.sha256(
        output).hexdigest(), hashlib.sha512(output).hexdigest()


def get_package_lines():
    package = get_hash_of_file('./Packages')
    package_gz = get_hash_of_file('./Packages.gz')
    package_size = os.stat('./Packages').st_size
    package_gz_size = os.stat('./Packages.gz').st_size

    return """\
MD5Sum:
 {md5}            {package_size} Packages
 {md5gz}            {package_gz_size} Packages.gz
SHA1:
 {SHA1}            {package_size} Packages
 {SHA1gz}            {package_gz_size} Packages.gz
SHA256:
 {SHA256}            {package_size} Packages
 {SHA256gz}            {package_gz_size} Packages.gz
SHA512:
 {SHA512}            {package_size} Packages
 {SHA512gz}            {package_gz_size} Packages.gz
    """.format(package_size=package_size,
               package_gz_size=package_gz_size,
               md5=package[0],
               md5gz=package_gz[0],
               SHA1=package[1],
               SHA1gz=package_gz[1],
               SHA256=package[2],
               SHA256gz=package_gz[2],
               SHA512=package[3],
               SHA512gz=package_gz[3],
               )


def main():
    output = """\
{header}
{body}
""".format(header=get_release_header(), body=get_package_lines())

    with open('./Release', 'w') as f:
        f.write(output)


if __name__ == '__main__':
    main()
