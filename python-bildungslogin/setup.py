#!/usr/bin/python3
import io
from setuptools import setup
from email.utils import parseaddr
from debian.changelog import Changelog
from debian.deb822 import Deb822


dch = Changelog(io.open('debian/changelog', 'r', encoding='utf-8'))
dsc = Deb822(io.open('debian/control', 'r', encoding='utf-8'))
realname, email_address = parseaddr(dsc['Maintainer'])

setup(
	packages=[
		'univention',
		'univention.bildungslogin',
		'univention.bildungslogin.licence_import',
	],
	package_dir={'': 'src'},
	entry_points={
		'console_scripts': [
			'bildungslogin-licence-import=univention.bildungslogin.licence_import.cmd:main',
		]
	},

	url='https://www.univention.de/',
	license='GNU Affero General Public License v3',
	name=dch.package,
	description='Python libs for the "Bildungslogin"',
	version=dch.version.full_version,
	maintainer=realname,
	maintainer_email=email_address,
)
