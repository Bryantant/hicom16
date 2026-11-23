# Hicom - User Delete Guard  (DocType Event: User / Before Delete)
# Hicom - User Rename Guard  (DocType Event: User / Before Rename)
#
# Same body for both events. Anyone who is not Administrator or System Manager cannot delete or
# rename an account that holds a protected role. User Manager may delete other users, so this is
# what keeps Hicom / System Manager accounts safe (the list filter only hides them).

actor = frappe.session.user
actor_roles = []
for row in frappe.db.sql(
	"select role from `tabHas Role` where parenttype = 'User' and parent = %s", actor
):
	actor_roles.append(row[0])

if actor != "Administrator" and "System Manager" not in actor_roles:
	protected = ["System Manager", "Administrator"]
	for row in frappe.db.sql(
		"select role from `tabHicom Protected Role` where parent = 'Hicom Subscription Settings'"
	):
		protected.append(row[0])

	held = frappe.db.sql(
		"""select count(*) from `tabHas Role`
		where parenttype = 'User' and parent = %(user)s and role in %(protected)s""",
		{"user": doc.name, "protected": tuple(protected)},
	)[0][0]
	if held:
		frappe.throw(_("You are not allowed to change this account. Please contact Hicom."))
