import frappe

# Relabel app titles shown in the desk workspace sidebar (the small subtitle
# under each workspace name, e.g. "ERPNext" beneath "Assets").
# Key = installed app_name, value = the title to display instead.
# Edit the value to rebrand; add more entries to relabel other apps.
APP_TITLE_OVERRIDES = {
	"erpnext": "Hicom System",
	"frappe": "Hicom Core",
}

# Replace app logos on the Desktop (Apps page) tiles and the sidebar app switcher.
# Key = installed app_name, value = asset URL of the logo to display instead.
APP_LOGO_OVERRIDES = {
	"erpnext": "/assets/hicom16/images/hicom-system.png",
}


def boot_session(bootinfo):
	"""Rewrite app titles and logos in the desk without touching core files.

	Wired via the `extend_bootinfo` hook, which runs in frappe.sessions.get()
	*after* frappe.boot.load_desktop_data has populated bootinfo.app_data, and
	on every request (including cached boots), so the relabel always applies.
	"""
	for app in bootinfo.get("app_data") or []:
		new_title = APP_TITLE_OVERRIDES.get(app.get("app_name"))
		if new_title:
			app["app_title"] = new_title
		new_logo = APP_LOGO_OVERRIDES.get(app.get("app_name"))
		if new_logo:
			app["app_logo_url"] = new_logo
		drop_unreachable_app_route(app)


def drop_unreachable_app_route(app):
	"""Clear an app's route when it names a workspace this user cannot open.

	ERPNext declares app_home "/desk/home", the Home workspace of module Setup. A user
	with Setup blocked cannot open it, so the desk reads "home" as a Page and fails
	with "No permission for Page" (BP admin.nota, 2026-10-19). With app_route empty the
	desk's landing ladder (sidebar.app_landing_route) opens the app's first dock entry
	the user can reach instead.
	"""
	route = app.get("app_route") or ""
	if not route.startswith("/desk/"):
		return
	slug = route[len("/desk/") :].strip("/")
	if not slug or "/" in slug:
		return

	from frappe.desk.desktop import get_workspaces
	from frappe.website.utils import cleanup_page_name

	workspaces = frappe.get_all("Workspace", filters={"public": 1}, pluck="name")
	target = next((w for w in workspaces if cleanup_page_name(w) == slug), None)
	if not target:
		return
	if target not in {page.name for page in get_workspaces()["pages"]}:
		app["app_route"] = ""
