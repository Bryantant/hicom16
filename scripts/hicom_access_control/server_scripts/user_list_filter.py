# Hicom - User List Filter  (Permission Query: User)
#
# Hides accounts that hold a protected role from anyone who is not Administrator or System Manager.
# Filters lists, link searches and reports only; opening the record by URL is still readable
# (writes are stopped by Hicom - User Access Guard). Locals: `user`, `conditions`.

user_roles = []
for row in frappe.db.sql(
	"select role from `tabHas Role` where parenttype = 'User' and parent = %s", user
):
	user_roles.append(row[0])

if user != "Administrator" and "System Manager" not in user_roles:
	protected = ["System Manager", "Administrator"]
	for row in frappe.db.sql(
		"select role from `tabHicom Protected Role` where parent = 'Hicom Subscription Settings'"
	):
		protected.append(row[0])

	escaped = []
	for role in protected:
		escaped.append(frappe.db.escape(role))

	conditions = f"""`tabUser`.name not in (
		select hr.parent from `tabHas Role` hr
		where hr.parenttype = 'User' and hr.role in ({", ".join(escaped)})
	)"""
