# hicom_user_seat_info  (API, logged-in users only)
#
# Called by the Hicom Client Scripts: frappe.call("hicom_user_seat_info")
# Returns {limit_on, limit, used, allowed_role_profiles, protected_roles}.
# The seat count must match Hicom - User Seat Limit - keep them in step.

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

used = frappe.db.sql(
	"""select count(*) from `tabUser` u
	where u.user_type = 'System User' and u.enabled = 1
		and u.name not in %(exempt_users)s
		and not exists (
			select 1 from `tabHas Role` hr
			where hr.parenttype = 'User' and hr.parent = u.name and hr.role in %(exempt_roles)s
		)""",
	{"exempt_users": tuple(exempt_users), "exempt_roles": tuple(exempt_roles)},
)[0][0]

protected = ["System Manager", "Administrator"]
for row in frappe.db.sql(
	"select role from `tabHicom Protected Role` where parent = 'Hicom Subscription Settings'"
):
	protected.append(row[0])

# Role Profiles that grant no protected role - the only ones a User Manager may pick
allowed_role_profiles = []
for row in frappe.db.sql(
	"""select rp.name from `tabRole Profile` rp
	where not exists (
		select 1 from `tabHas Role` hr
		where hr.parenttype = 'Role Profile' and hr.parent = rp.name and hr.role in %(protected)s
	)
	order by rp.name""",
	{"protected": tuple(protected)},
):
	allowed_role_profiles.append(row[0])

frappe.response["message"] = {
	"limit_on": frappe.utils.cint(
		frappe.db.get_single_value("Hicom Subscription Settings", "enable_user_limit")
	),
	"limit": frappe.utils.cint(frappe.db.get_single_value("Hicom Subscription Settings", "max_users")),
	"used": used,
	"allowed_role_profiles": allowed_role_profiles,
	"protected_roles": protected,
}
