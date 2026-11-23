"""Check Hicom Subscription & Access Control on a site, end to end.

Creates throwaway users/role profiles, acts as a User Manager, and checks every rule.
Everything runs in one transaction that is rolled back at the end - nothing is left behind.

    cd <bench>/sites
    ../env/bin/python ../apps/hicom16/scripts/hicom_access_control/verify.py --site bp.localhost
"""

import argparse
import sys

DOMAIN = "hicom-verify.test"
SETTINGS = "Hicom Subscription Settings"
TEST_PROFILES = ("Verify Staff", "Verify Admin")
results = []


def email(local):
	return f"{local}@{DOMAIN}"


def check(label, fn, expect_error=None):
	"""Run fn; pass if it returns truthy (expect_error=None) or raises containing expect_error."""
	import frappe

	try:
		out = fn()
	except Exception as e:
		msg = str(e) or type(e).__name__
		ok = expect_error is not None and expect_error.lower() in f"{type(e).__name__} {msg}".lower()
		results.append((ok, label, f"raised {type(e).__name__}: {msg[:140]}"))
		frappe.clear_messages()
		return None
	ok = expect_error is None and out is not False
	results.append((ok, label, "ok" if ok else f"expected error '{expect_error}', got none"))
	return out


def as_user(user):
	import frappe

	frappe.set_user(user)


def new_user(local, profiles=(), roles=(), enabled=1):
	import frappe

	doc = frappe.get_doc(
		{
			"doctype": "User",
			"email": email(local),
			"first_name": f"Verify {local}",
			"send_welcome_email": 0,
			"enabled": enabled,
			"role_profiles": [{"role_profile": p} for p in profiles],
			"roles": [{"role": r} for r in roles],
		}
	)
	doc.insert()
	return doc


def set_settings(**values):
	import frappe

	actor = frappe.session.user
	as_user("Administrator")
	s = frappe.get_single(SETTINGS)
	for key, value in values.items():
		if key in ("exempt_users",):
			s.set(key, [{"user": v} for v in value])
		else:
			s.set(key, value)
	s.save()
	as_user(actor)


def seat_info():
	import frappe

	frappe.get_doc("Server Script", "Hicom - User Seat Info").execute_method()
	return frappe.response["message"]


def run():
	import frappe

	as_user("Administrator")
	# an enabled role: a site that disabled unused roles (NG did) would otherwise hand the test profile a role that grants nothing
	desk_role = next(
		r
		for r in ("Sales User", "Stock User", "Accounts User", "Blogger", "Asset Editor")
		if frappe.db.exists("Role", {"name": r, "disabled": 0})
	)
	for name, role in zip(TEST_PROFILES, (desk_role, "System Manager"), strict=True):
		frappe.get_doc({"doctype": "Role Profile", "role_profile": name, "roles": [{"role": role}]}).insert()

	# the site's real limit may already be reached - lift it before creating the test users
	# (rolled back with everything else)
	set_settings(enable_user_limit=1, max_users=0)
	sm = new_user("sm", roles=["System Manager"])
	um = new_user("um", roles=["User Manager"])

	# --- access rules, acting as User Manager -------------------------------------------------
	as_user(um.name)
	staff = check(
		"UM creates user with an allowed Role Profile -> System User",
		lambda: new_user("staff1", profiles=["Verify Staff"]),
	)
	check("  ...and it got the profile's role", lambda: staff and desk_role in [r.role for r in staff.roles])
	check("  ...and it is a System User", lambda: staff and staff.user_type == "System User")
	check(
		"UM cannot use a Role Profile that grants System Manager",
		lambda: new_user("bad1", profiles=["Verify Admin"]),
		expect_error="not allowed to give",
	)
	check(
		"UM cannot add System Manager directly",
		lambda: new_user("bad2", roles=["System Manager"]),
		expect_error="not allowed to give",
	)
	check(
		"UM cannot add a normal role without a Role Profile",
		lambda: new_user("bad3", roles=[desk_role]),
		expect_error="Role Profile",
	)

	def switch_to_admin_profile():
		doc = frappe.get_doc("User", staff.name)
		doc.role_profiles = []
		doc.append("role_profiles", {"role_profile": "Verify Admin"})
		doc.save()

	check(
		"UM cannot switch a user to a System Manager profile",
		switch_to_admin_profile,
		expect_error="not allowed to give",
	)

	def edit_staff():
		doc = frappe.get_doc("User", staff.name)
		doc.last_name = "Edited"
		doc.save()
		return True

	check("UM can edit a normal user", edit_staff)

	def edit_sm(field, value):
		doc = frappe.get_doc("User", sm.name)
		doc.set(field, value)
		doc.save()

	check(
		"UM cannot edit a System Manager account",
		lambda: edit_sm("last_name", "Hacked"),
		expect_error="not allowed to change",
	)
	check(
		"UM cannot disable a System Manager account",
		lambda: edit_sm("enabled", 0),
		expect_error="not allowed to change",
	)
	check(
		"UM cannot rename a System Manager account",
		lambda: frappe.rename_doc("User", sm.name, email("sm2")),
		expect_error="not allowed to change",
	)
	check(
		"UM cannot delete a System Manager account",
		lambda: frappe.delete_doc("User", sm.name),
		expect_error="not allowed to change",
	)
	check(
		"User list hides System Manager accounts from UM",
		lambda: sm.name not in frappe.get_list("User", pluck="name", limit_page_length=0)
		and staff.name in frappe.get_list("User", pluck="name", limit_page_length=0),
	)
	check(
		"UM cannot open Hicom Subscription Settings",
		lambda: not frappe.has_permission(SETTINGS, "read"),
	)
	check("UM cannot edit Role Profiles", lambda: not frappe.has_permission("Role Profile", "write"))
	check(
		"Seat info offers only safe Role Profiles",
		lambda: "Verify Staff" in seat_info()["allowed_role_profiles"]
		and "Verify Admin" not in seat_info()["allowed_role_profiles"],
	)

	check(
		"Seat info lists the protected roles (hidden from the role editor)",
		lambda: {"System Manager", "Script Manager"} <= set(seat_info()["protected_roles"]),
	)

	# --- seat limit ---------------------------------------------------------------------------
	used = seat_info()["used"]
	set_settings(max_users=used)
	check(
		f"At the limit ({used}/{used}) a new desk user is blocked",
		lambda: new_user("over1", profiles=["Verify Staff"]),
		expect_error="User limit reached",
	)
	def portal_signup_at_limit():
		actor = frappe.session.user
		as_user("Guest")
		try:
			doc = frappe.get_doc({"doctype": "User", "email": email("portal1"), "first_name": "Portal", "send_welcome_email": 0})
			doc.insert(ignore_permissions=True)
			user_type = doc.user_type
		finally:
			as_user(actor)
		return user_type == "Website User" and seat_info()["used"] == used

	check("Portal sign-up (Guest) at the limit is allowed and not counted", portal_signup_at_limit)

	def disable_staff():
		doc = frappe.get_doc("User", staff.name)
		doc.enabled = 0
		doc.save()
		return True

	check(
		"Quick Entry: a new user with no role is refused at the limit",
		lambda: new_user("qe1"),
		expect_error="User limit reached",
	)

	check("UM can disable a normal user", disable_staff)
	check("Disabled users do not count: seat info drops by one", lambda: seat_info()["used"] == used - 1)
	check(
		"A user created disabled at the limit is allowed and not counted",
		lambda: new_user("dis1", profiles=["Verify Staff"], enabled=0) and seat_info()["used"] == used - 1,
	)

	def enable_staff():
		doc = frappe.get_doc("User", staff.name)
		doc.enabled = 1
		doc.save()
		return True

	check("Re-enabling a user while a seat is free works", lambda: enable_staff() and seat_info()["used"] == used)
	check("UM can disable the user again", disable_staff)
	check("Disabling freed a seat: a new user is allowed", lambda: new_user("over3", profiles=["Verify Staff"]))
	check("Re-enabling a disabled user at the limit is blocked", enable_staff, expect_error="User limit reached")

	def free_seat_and_enable():
		frappe.delete_doc("User", email("over3"))
		return enable_staff()

	check("Re-enabling works again once a seat is freed", free_seat_and_enable)

	check("Editing an existing user at the limit still works", edit_staff)

	def delete_then_create():
		frappe.delete_doc("User", email("portal1"))  # portal user, frees nothing
		frappe.delete_doc("User", staff.name)
		return new_user("fill3", profiles=["Verify Staff"])

	check("UM can delete a normal user, and that frees a seat", delete_then_create)

	set_settings(exempt_users=[email("fill3")])
	check("Users Not Counted: exempting a user frees a seat", lambda: new_user("fill2", profiles=["Verify Staff"]))

	as_user("Administrator")
	check("Roles Not Counted: System Manager user can be created", lambda: new_user("sm3", roles=["System Manager"]))
	check(
		"Limit applies to System Manager too",
		lambda: new_user("over2", roles=[desk_role]),
		expect_error="User limit reached",
	)

	as_user(um.name)
	set_settings(max_users=0)
	check("Limit 0 means no limit", lambda: new_user("free1", profiles=["Verify Staff"]))
	check("Limit 0: Quick Entry user with no role is created", lambda: new_user("qe2"))
	set_settings(max_users=used, enable_user_limit=0)
	check("Limit switched off means no limit", lambda: new_user("free2", profiles=["Verify Staff"]))


def main():
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--site", required=True)
	parser.add_argument("--sites-path", default=".")
	args = parser.parse_args()

	import frappe

	frappe.init(site=args.site, sites_path=args.sites_path)
	frappe.connect()
	try:
		run()
	finally:
		frappe.db.rollback()
		# Role Profile.on_update locks the doc (a file on disk) for a queued job the rollback cancels
		from frappe.utils.file_lock import delete_lock

		for name in TEST_PROFILES:
			profile = frappe.new_doc("Role Profile")
			profile.name = name
			delete_lock(profile.get_signature())
		frappe.set_user("Administrator")
		frappe.clear_cache()
		frappe.destroy()

	for ok, label, detail in results:
		print(f"{'PASS' if ok else 'FAIL'}  {label}" + ("" if ok else f"   <- {detail}"))
	failed = sum(1 for ok, *_ in results if not ok)
	print(f"\n{len(results) - failed}/{len(results)} passed (all changes rolled back)")
	sys.exit(1 if failed else 0)


if __name__ == "__main__":
	main()
