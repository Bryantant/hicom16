# Hicom - User Seat Limit  (DocType Event: User / Before Save)
#
# Blocks a save that would take the site over the user limit in Hicom Subscription Settings.
# A seat is any enabled System User that is not Administrator/Guest, not in Exempt Users and
# holds no Exempt Role. Disabled users never count (Bry, 2026-10-30; before that they did). Website (portal) users never count. Applies to everyone, System Manager
# included - Hicom exempts its own accounts through the settings instead.
#
# Disabling a user frees a seat; re-enabling takes it back, so it is blocked at the limit. Only checked when this
# save turns the user into a seat (new user, Website -> System User, exemption removed, re-enabled), so editing or
# disabling an existing seat never gets blocked.
# A user made from the desk (Quick Entry or New User) starts as a Website User because it holds no role yet, so it
# would slip past the check until a role is given. A new user made by someone signed in therefore counts as a seat
# from the first save. Portal sign-ups (Guest) are not affected.
# The same seat count lives in the hicom_user_seat_info API script - keep them in step.


def takes_seat(user_doc, exempt_users, exempt_roles):
    if not user_doc or user_doc.user_type != "System User" or not user_doc.enabled:
        return False
    if user_doc.name in exempt_users:
        return False
    for d in user_doc.roles:
        if d.role in exempt_roles:
            return False
    return True


def new_from_desk(user_doc, exempt_users, exempt_roles):
    if not user_doc or not user_doc.is_new() or not user_doc.enabled or frappe.session.user == "Guest":
        return False
    if user_doc.name in exempt_users:
        return False
    for d in user_doc.roles:
        if d.role in exempt_roles:
            return False
    return True


limit = frappe.utils.cint(frappe.db.get_single_value("Hicom Subscription Settings", "max_users"))
limit_on = frappe.db.get_single_value("Hicom Subscription Settings", "enable_user_limit")

if limit_on and limit > 0:
    exempt_users = ["Administrator", "Guest"]
    for row in frappe.db.sql(
        "select user from `tabHicom Seat Exempt User` where parent = 'Hicom Subscription Settings'"
    ):
        exempt_users.append(row[0])

    exempt_roles = [""]
    for row in frappe.db.sql(
        "select role from `tabHicom Seat Exempt Role` where parent = 'Hicom Subscription Settings'"
    ):
        exempt_roles.append(row[0])

    if (
        takes_seat(doc, exempt_users, exempt_roles) or new_from_desk(doc, exempt_users, exempt_roles)
    ) and not takes_seat(doc.get_doc_before_save(), exempt_users, exempt_roles):
        used = frappe.db.sql(
            """select count(*) from `tabUser` u
            where u.user_type = 'System User' and u.enabled = 1
                and u.name not in %(exempt_users)s and u.name != %(me)s
                and not exists (
                    select 1 from `tabHas Role` hr
                    where hr.parenttype = 'User' and hr.parent = u.name and hr.role in %(exempt_roles)s
                )""",
            {"exempt_users": tuple(exempt_users), "exempt_roles": tuple(exempt_roles), "me": doc.name},
        )[0][0]

        if used >= limit:
            frappe.throw(
                f"User limit reached ({used} of {limit} users). "
                "Contact Hicom to add more users.",
                title=_("User Limit Reached"),
            )
