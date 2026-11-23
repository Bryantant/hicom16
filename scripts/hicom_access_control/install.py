"""Install Hicom Subscription & Access Control on one site.

Creates everything as ordinary site records (custom Module Def, Custom DocTypes, Role,
permissions, Server Scripts, Client Scripts), so it all stays editable in the UI afterwards.
Safe to re-run: missing pieces are created, existing ones are left alone. Script bodies that
differ from the files here are only overwritten with --update-scripts (so UI edits made in
production are not silently lost).

Run from the bench's sites directory with the bench's python:

    cd <bench>/sites
    ../env/bin/python ../apps/hicom16/scripts/hicom_access_control/install.py --site bp.localhost
"""

import argparse
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = "Hicom"
SETTINGS = "Hicom Subscription Settings"
USER_MANAGER = "User Manager"

CHILD_TABLES = {
	"Hicom Seat Exempt User": {"fieldname": "user", "label": "User", "options": "User"},
	"Hicom Seat Exempt Role": {"fieldname": "role", "label": "Role", "options": "Role"},
	"Hicom Protected Role": {"fieldname": "role", "label": "Role", "options": "Role"},
}

SETTINGS_FIELDS = [
	{"fieldname": "user_limit_section", "fieldtype": "Section Break", "label": "User Limit"},
	{
		"fieldname": "enable_user_limit",
		"fieldtype": "Check",
		"label": "Enable User Limit",
		"description": "When off, any number of users can be created.",
	},
	{
		"fieldname": "max_users",
		"fieldtype": "Int",
		"label": "Maximum Users",
		"description": "How many enabled desk users the client may have, disabled users not counted. 0 means no limit.",
		"depends_on": "enable_user_limit",
	},
	{"fieldname": "seat_usage", "fieldtype": "HTML", "label": "Seat Usage"},
	{"fieldname": "column_break_limit", "fieldtype": "Column Break"},
	{
		"fieldname": "exempt_users",
		"fieldtype": "Table MultiSelect",
		"label": "Users Not Counted",
		"options": "Hicom Seat Exempt User",
		"description": "Administrator, Guest and portal (Website) users are never counted.",
	},
	{
		"fieldname": "exempt_roles",
		"fieldtype": "Table MultiSelect",
		"label": "Roles Not Counted",
		"options": "Hicom Seat Exempt Role",
		"description": "Users holding any of these roles are not counted (e.g. Hicom's System Manager accounts).",
	},
	{"fieldname": "access_section", "fieldtype": "Section Break", "label": "User Manager Access"},
	{
		"fieldname": "protected_roles",
		"fieldtype": "Table MultiSelect",
		"label": "Protected Roles",
		"options": "Hicom Protected Role",
		"description": "Roles a User Manager can never give, and accounts holding them are hidden "
		"from the User Manager and cannot be changed by them. System Manager and Administrator "
		"are always protected.",
	},
]

SERVER_SCRIPTS = [
	{
		"name": "Hicom - User Access Guard",
		"script_type": "DocType Event",
		"reference_doctype": "User",
		"doctype_event": "Before Save",
		"file": "user_access_guard.py",
	},
	{
		"name": "Hicom - User Seat Limit",
		"script_type": "DocType Event",
		"reference_doctype": "User",
		"doctype_event": "Before Save",
		"file": "user_seat_limit.py",
	},
	{
		"name": "Hicom - User Delete Guard",
		"script_type": "DocType Event",
		"reference_doctype": "User",
		"doctype_event": "Before Delete",
		"file": "protected_account_guard.py",
	},
	{
		"name": "Hicom - User Rename Guard",
		"script_type": "DocType Event",
		"reference_doctype": "User",
		"doctype_event": "Before Rename",
		"file": "protected_account_guard.py",
	},
	{
		"name": "Hicom - User List Filter",
		"script_type": "Permission Query",
		"reference_doctype": "User",
		"file": "user_list_filter.py",
	},
	{
		"name": "Hicom - User Seat Info",
		"script_type": "API",
		"api_method": "hicom_user_seat_info",
		"file": "user_seat_info.py",
	},
]

CLIENT_SCRIPTS = [
	{"name": "Hicom - User Form", "dt": "User", "file": "user_form.js"},
	{"name": "Hicom - Subscription Settings Form", "dt": SETTINGS, "file": "subscription_settings_form.js"},
]

# (doctype, permlevel, rights) granted to User Manager. Disabling or deleting a user
# frees a seat (disabled users do not count); protected accounts are covered by the Delete Guard.
USER_MANAGER_PERMS = [
	("User", 0, ["read", "write", "create", "delete", "report"]),
	("User", 1, ["read", "write"]),
	("Role Profile", 0, ["read"]),
	("Role Profile", 1, ["read"]),
	("Module Profile", 0, ["read"]),
]


def log(msg):
	print(f"  {msg}")


def read_file(folder, name):
	with open(os.path.join(HERE, folder, name)) as f:
		return f.read()


def ensure_module():
	import frappe

	if frappe.db.exists("Module Def", MODULE):
		return
	# app_name is mandatory even for custom modules; frappe is the one app every site has
	frappe.get_doc({"doctype": "Module Def", "module_name": MODULE, "custom": 1, "app_name": "frappe"}).insert()
	log(f"created Module Def {MODULE}")


def ensure_doctype(name, spec, fields):
	"""Create the Custom DocType, or append any fields it is missing (never removes or edits)."""
	import frappe

	if not frappe.db.exists("DocType", name):
		doc = frappe.get_doc({"doctype": "DocType", "name": name, "module": MODULE, "custom": 1, **spec})
		for field in fields:
			doc.append("fields", field)
		doc.insert()
		log(f"created DocType {name}")
		return

	doc = frappe.get_doc("DocType", name)
	existing = {f.fieldname for f in doc.fields}
	missing = [f for f in fields if f["fieldname"] not in existing]
	for field in missing:
		doc.append("fields", field)
	if missing:
		doc.save()
		log(f"added fields to {name}: {', '.join(f['fieldname'] for f in missing)}")


def ensure_doctypes():
	for name, link in CHILD_TABLES.items():
		ensure_doctype(
			name,
			{"istable": 1, "editable_grid": 1},
			[{"fieldtype": "Link", "reqd": 1, "in_list_view": 1, **link}],
		)

	ensure_doctype(
		SETTINGS,
		{
			"issingle": 1,
			"permissions": [
				{"role": "System Manager", "read": 1, "write": 1, "create": 1, "print": 1, "email": 1}
			],
		},
		SETTINGS_FIELDS,
	)


def ensure_role():
	import frappe

	if frappe.db.exists("Role", USER_MANAGER):
		return
	frappe.get_doc({"doctype": "Role", "role_name": USER_MANAGER, "desk_access": 1}).insert()
	log(f"created Role {USER_MANAGER}")


def ensure_permissions():
	"""Grant User Manager its rights. add_permission() copies the standard DocPerms into Custom
	DocPerm first, so System Manager keeps its access (Custom DocPerm replaces standard rows)."""
	import frappe
	from frappe.permissions import add_permission, update_permission_property

	for doctype, permlevel, rights in USER_MANAGER_PERMS:
		row = frappe.db.get_value(
			"Custom DocPerm",
			{"parent": doctype, "role": USER_MANAGER, "permlevel": permlevel, "if_owner": 0},
			rights,
			as_dict=True,
		)
		if row and all(row[r] for r in rights):
			continue
		if not row:
			add_permission(doctype, USER_MANAGER, permlevel)
		for right in rights:
			update_permission_property(doctype, USER_MANAGER, permlevel, right, 1)
		frappe.clear_cache(doctype=doctype)
		log(f"granted {USER_MANAGER} {'/'.join(rights)} on {doctype} (level {permlevel})")


def seed_settings():
	"""Fill the settings tables only when empty - never overwrite what Hicom set on the site."""
	import frappe

	settings = frappe.get_single(SETTINGS)
	changed = False
	if not settings.exempt_roles:
		settings.append("exempt_roles", {"role": "System Manager"})
		changed = True
	if not settings.protected_roles:
		for role in ("System Manager", "Script Manager"):
			settings.append("protected_roles", {"role": role})
		changed = True
	if changed:
		settings.save()
		log(f"seeded {SETTINGS} (exempt: System Manager; protected: System Manager, Script Manager)")


def upsert_script(doctype, name, values, update):
	import frappe

	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, "name": name, **values}).insert(set_name=name)
		log(f"created {doctype} {name}")
		return

	doc = frappe.get_doc(doctype, name)
	if doc.script == values["script"]:
		return
	if not update:
		log(f"SKIPPED {doctype} {name}: differs from the file here (re-run with --update-scripts)")
		return
	doc.update(values)
	doc.save()
	log(f"updated {doctype} {name}")


def ensure_scripts(update):
	for s in SERVER_SCRIPTS:
		values = {k: v for k, v in s.items() if k not in ("name", "file")}
		values.update(script=read_file("server_scripts", s["file"]), module=MODULE, disabled=0)
		upsert_script("Server Script", s["name"], values, update)

	for s in CLIENT_SCRIPTS:
		values = {
			"dt": s["dt"],
			"view": "Form",
			"enabled": 1,
			"module": MODULE,
			"script": read_file("client_scripts", s["file"]),
		}
		upsert_script("Client Script", s["name"], values, update)


def install(update_scripts=False):
	import frappe

	if not frappe.conf.get("server_script_enabled"):
		print("WARNING: server_script_enabled is off in common_site_config.json - the guards will not run.")

	ensure_module()
	ensure_doctypes()
	ensure_role()
	ensure_permissions()
	seed_settings()
	ensure_scripts(update_scripts)


def main():
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--site", required=True)
	parser.add_argument("--sites-path", default=".")
	parser.add_argument("--update-scripts", action="store_true", help="overwrite script bodies that differ")
	args = parser.parse_args()

	import frappe

	frappe.init(site=args.site, sites_path=args.sites_path)
	frappe.connect()
	try:
		print(f"Installing Hicom Subscription & Access Control on {args.site}")
		install(update_scripts=args.update_scripts)
		frappe.db.commit()
		frappe.clear_cache()
		print("Done.")
	except Exception:
		frappe.db.rollback()
		raise
	finally:
		frappe.destroy()


if __name__ == "__main__":
	main()
