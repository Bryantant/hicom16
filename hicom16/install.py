import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

BRAND_NAME = "Hicom System"
BRAND_LOGO = "/assets/hicom16/images/hicom-system.png"

# (doctype, field, value, values that count as "not customised yet").
# A field is filled only while it is empty or still holds the stock Frappe/ERPNext value, so a
# name or logo someone set in the UI is never overwritten, however often this runs.
BRANDING = [
	("Website Settings", "app_name", BRAND_NAME, ("", None, "Frappe")),
	("Website Settings", "app_logo", BRAND_LOGO, ("", None)),
	("Website Settings", "favicon", BRAND_LOGO, ("", None)),
	("Website Settings", "splash_image", BRAND_LOGO, ("", None)),
	("System Settings", "app_name", BRAND_NAME, ("", None, "Frappe", "ERPNext")),
	("Navbar Settings", "app_logo", BRAND_LOGO, ("", None)),
]


def apply_branding():
	"""Fill the branding fields of the Single doctypes that Hicom System controls.

	Idempotent, so it is safe from `after_install` (new sites) and from a patch (existing sites).
	Not wired to `after_migrate` on purpose: that would run on every migrate.
	"""
	changed = []
	for doctype, field, value, unset in BRANDING:
		if not frappe.get_meta(doctype).has_field(field):
			continue
		if frappe.db.get_single_value(doctype, field) in unset:
			frappe.db.set_single_value(doctype, field, value)
			changed.append(f"{doctype}.{field}")
	if changed:
		frappe.clear_cache()
	return changed


# (doctype, fieldname, property, value, property_type). Applied through Property Setters, so the core
# doctype files stay untouched. Re-running replaces the setter for the same field and property, so
# a hand-made Customize Form change to one of these exact properties is overwritten.
PROPERTY_SETTERS = [
	# User > API Access: drop the token-authentication documentation link under Generate Keys
	("User", "generate_keys", "description", "", "Small Text"),
	# User > Security Settings: hide the Third Party Authentication section
	("User", "third_party_authentication", "hidden", 1, "Check"),
	# User > Settings: hide the App section (Default App)
	("User", "app_section", "hidden", 1, "Check"),
	# One session per user. The default only applies to users created from now on; users that
	# already exist keep the value stored on them (2 unless changed).
	("User", "simultaneous_sessions", "default", "1", "Text"),
	("User", "simultaneous_sessions", "hidden", 1, "Check"),
	# Item form: field help text that names the product ("ERPNext will make ...")
	("Item", "is_stock_item", "description",
	 "A stock ledger entry is made for each transaction of this item. Keep unchecked for non-stock or service items.",
	 "Small Text"),
	# Accounts Settings: help text that is only a link to the product documentation
	("Accounts Settings", "enable_common_party_accounting", "description", "", "Small Text"),
]


def apply_property_setters():
	"""Create or refresh the Property Setters above. Idempotent."""
	doctypes = set()
	for doctype, fieldname, prop, value, prop_type in PROPERTY_SETTERS:
		make_property_setter(doctype, fieldname, prop, value, prop_type, validate_fields_for_doctype=False)
		doctypes.add(doctype)
	for doctype in doctypes:
		frappe.clear_cache(doctype=doctype)


def after_install():
	apply_branding()
	apply_property_setters()
