from hicom16.install import apply_property_setters


def execute():
	"""Re-apply every Property Setter in install.PROPERTY_SETTERS (idempotent).

	A patch runs once per line of patches.txt, and Frappe reads the module name from the first word of the line
	(`patchmodule.split(maxsplit=1)[0]`), so the same module can run again under a new line: append a short tag
	after the module name whenever an entry is added to the list, for example
	`hicom16.patches.v16_0.apply_property_setters  # 2026-11-22 accounts settings help`.
	"""
	apply_property_setters()
