import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	"""Remove the token-based authentication documentation link under Generate Keys (User > API Access)."""
	make_property_setter("User", "generate_keys", "description", "", "Small Text", validate_fields_for_doctype=False)
	frappe.clear_cache(doctype="User")
