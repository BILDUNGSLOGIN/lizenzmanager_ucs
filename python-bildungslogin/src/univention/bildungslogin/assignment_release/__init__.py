from univention.bildungslogin.models import Status

from univention.admin.uldap import getAdminConnection
from univention.bildungslogin.models import LicenseType
from univention.udm import UDM


def free_assignment_if_possible(assignment):
    if assignment.props.status == Status.ASSIGNED:
        assignment.props.status = Status.AVAILABLE
        assignment.props.time_of_assignment = None
        assignment.props.assignee = None

        assignment.save()
        return True
    return False


def cleanup_assignments(entry_uuid):
    lo, _ = getAdminConnection()
    udm_license = UDM(lo).version(2).get('bildungslogin/license')
    udm_assignment = UDM(lo).version(2).get('bildungslogin/assignment')

    for assignment in udm_assignment.search('(assignee=' + entry_uuid + ')'):
        license = udm_license.get(",".join(assignment.dn.split(',')[1:]))
        if license.props.license_type == LicenseType.SINGLE:
            free_assignment_if_possible(assignment)
        elif license.props.license_type == LicenseType.VOLUME:
            if not free_assignment_if_possible(assignment):
                assignment.delete()
