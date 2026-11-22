from hicom16.install import apply_property_setters


def execute():
	"""Item > Maintain Stock help text without the product name. A new Property Setter in the list needs a new patch:
	a patch runs once per site, so the earlier apply_user_property_setters does not run again."""
	apply_property_setters()
