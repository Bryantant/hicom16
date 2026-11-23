# Hicom - User Access Guard  (DocType Event: User / Before Save)
#
# Anyone who is not Administrator or System Manager (i.e. a client's User Manager):
#   - cannot change an account that holds a protected role (Hicom / System Manager accounts)
#   - cannot grant a protected role, directly or through a Role Profile
#   - can only change a user's roles by choosing Role Profiles
#   - cannot set a custom User Type
#
# Runs after User.validate, so roles are already rebuilt from role_profiles and user_type is final.
# Note: str.format is blocked in Server Scripts (use f-strings), and safe_exec runs with separate
# globals/locals, so no helper functions or comprehensions that read top-level names - plain loops.

actor = frappe.session.user
actor_roles = []
for row in frappe.db.sql(
	"select role from `tabHas Role` where parenttype = 'User' and parent = %s", actor
):
	actor_roles.append(row[0])

if actor != "Administrator" and "System Manager" not in actor_roles:
	protected = set(["System Manager", "Administrator"])
	for row in frappe.db.sql(
		"select role from `tabHicom Protected Role` where parent = 'Hicom Subscription Settings'"
	):
		protected.add(row[0])

	old = doc.get_doc_before_save()
	old_roles = set()
	if old:
		for d in old.roles:
			old_roles.add(d.role)

	if old_roles & protected:
		frappe.throw(_("You are not allowed to change this account. Please contact Hicom."))

	new_roles = set()
	for d in doc.roles:
		new_roles.add(d.role)

	granted = sorted(new_roles & protected)
	if granted:
		frappe.throw(f"You are not allowed to give these roles: {', '.join(granted)}")

	if not doc.role_profiles and new_roles != old_roles:
		frappe.throw(_("Give access by choosing a Role Profile, not individual roles."))

	if doc.user_type not in ("System User", "Website User"):
		frappe.throw(f"You are not allowed to set User Type {doc.user_type}.")
