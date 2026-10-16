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
