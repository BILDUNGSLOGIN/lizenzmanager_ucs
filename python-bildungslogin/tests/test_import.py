import pytest

from univention.bildungslogin.licence_import import import_licences


def test_licence_import():
	with pytest.raises(NotImplementedError):
		import_licences('fake_path')
