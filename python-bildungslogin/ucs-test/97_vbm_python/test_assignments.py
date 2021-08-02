import datetime
import pytest
import univention.testing.ucsschool.ucs_test_school as utu
from univention.bildungslogin.utils import Status


def license_was_assigned_correct_to_user(assignments, username):
    assignment = None
    for a in assignments:
        if a.assignee == username:
            assignment = a
    assert username == assignment.assignee
    assert Status.ASSIGNED == assignment.status
    # todo check after fix of my vm
    assert assignment.time_of_assignment == datetime.datetime.now().strftime("%Y-%m-%m")


# todo test special type ?
@pytest.mark.parametrize("user_type", ["student", "teacher"])
def test_assign_user_to_license(assignment_handler, licence_handler, random_license, user_type):
    # 00_vbm_test_assignments
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        random_license.license_school = ou
        licence_handler.create(random_license)
        if user_type == "student":
            username = schoolenv.create_student(ou)[0]
        elif user_type == "teacher":
            username = schoolenv.create_teacher(ou)[0]

        assignment_handler.assign_to_license(username=username, license_code=random_license.license_code)
        # todo
        # this should not be possible
        # with pytest.raises(BiloStatusChange):
        #     assignment_handler.assign_to_license(username=username, license_code=random_license.license_code)
        assignments = licence_handler.get_assignments_for_license(random_license)
        license_was_assigned_correct_to_user(assignments, username)


def test_assign_users_to_licenses(assignment_handler, licence_handler, random_license):
    # 00_vbm_test_assignments
    with utu.UCSTestSchool() as schoolenv:
        ou, _ = schoolenv.create_ou()
        random_license.license_school = ou
        licence_handler.create(random_license)
        users = [schoolenv.create_student(ou)[0] for _ in range(random_license.license_quantity)]
        assignment_handler.assign_users_to_license(
            usernames=users,
            licenses_code=random_license.license_code
        )
        assignments = licence_handler.get_assignments_for_license(random_license)
        for user in users:
            license_was_assigned_correct_to_user(assignments, user)


#
#
# def test_get_assignments_for_product_id_for_user():
#     pass
#
#

#
#
# def test_change_license_status(username, status):
#     pass


def test_is_valid_status_change():
    # check if error was raised in udm
    pass