from hicom16.install import apply_property_setters


def execute():
	"""Hide Third Party Authentication and App on User, one simultaneous session by default.

	Also covers the API Access link, which hide_user_api_docs_link only applied to sites that
	existed when it was added: a fresh install marks every patch as done without running it.
	"""
	apply_property_setters()
