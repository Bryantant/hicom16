// Hicom16 desk overrides.
// (The "start with sidebar closed on form/list pages" rule was removed on 2026-10-16: in v16.50 the
// form's Print icon lives in the form sidebar, so hiding .layout-side-section hid Print on desktop.)

// Hicom16: hide Frappe/ERPNext documentation links from the desk.
//
// v16 reads every "Documentation" link from metadata: DocType.documentation (form, list,
// kanban menus and the empty-list state), Report.documentation_url (report menu) and
// DocField.documentation_url (field, grid and info-card links). All of it reaches the
// browser through frappe.model.sync (boot docs and every frappe.call response), and this
// file loads before the desk boots, so blanking the values here hides every such link for
// all apps without touching the database.
(function hideDocumentationLinks() {
	// Forms where these values are edited: leave them intact so saving does not blank them.
	var EDIT_FORMS = ["DocType", "Report", "Customize Form"];

	function is_edit_form() {
		var route = frappe.get_route ? frappe.get_route() : null;
		return !!route && route[0] === "Form" && EDIT_FORMS.indexOf(route[1]) !== -1;
	}

	function strip(doc) {
		if (!doc) return;
		if (doc.doctype === "DocType") {
			doc.documentation = null;
			(doc.fields || []).forEach(function (df) {
				df.documentation_url = null;
			});
		} else if (doc.doctype === "Report") {
			doc.documentation_url = null;
		}
	}

	var original_sync = frappe.model.sync;
	frappe.model.sync = function (r) {
		if (r && !is_edit_form()) {
			var docs = r.docs || (r.docinfo ? null : r);
			if (Array.isArray(docs)) docs.forEach(strip);
			else if ($.isPlainObject(docs)) strip(docs);
		}
		return original_sync.apply(this, arguments);
	};

	// Per-page links under Help (frappe.help.help_links): keep the registry empty, including
	// links other apps register after this file loads.
	frappe.provide("frappe.help");
	frappe.help.help_links = new Proxy(
		{},
		{
			get: function () {
				return undefined;
			},
			set: function () {
				return true;
			},
		}
	);
})();

// Hicom16: hide the remaining Frappe links. These live in frappe.boot, which is already set
// when this file runs and is read only later, so they are switched off here. (Doing it in the
// extend_bootinfo hook does not work: frappe.sessions sets navbar_settings and the navigation
// prompt after the hook runs, and navbar_settings is a shared cached doc.)
(function hideFrappeLinks() {
	var boot = frappe.boot || {};

	// Help menu: hide About (frappe.io / forum dialog) and every row leading to frappe.io;
	// keep System Health for System Managers only.
	var help = (boot.navbar_settings && boot.navbar_settings.help_dropdown) || [];
	help.forEach(function (item) {
		if ((item.action || "").indexOf("show_about") !== -1 || /frappe\.io/i.test(item.route || "")) {
			item.hidden = 1;
		} else if ((item.route || "").indexOf("system-health-report") !== -1) {
			item.condition = "frappe.user.has_role('System Manager')";
		}
	});

	// "Switch to Frappe CRM / Helpdesk" banners in the CRM and Support sidebars.
	if (boot.sysdefaults) boot.sysdefaults.disable_product_suggestion = 1;

	// One-time "Try the new navigation" dialog linking to docs.frappe.io.
	boot.show_new_navigation_prompt = false;
})();

// Hicom16: avatar menu on the apps screen (/desk). DesktopPage.setup_avatar hard-codes "About"
// (frappe.io dialog) and "Frappe Support" (support.frappe.io) and builds its Dropdown in one go,
// with no hook to drop rows. The "desktop_screen" event fires on the instance just before
// setup_avatar runs, so wrap that call once and filter the rows handed to frappe.ui.Dropdown.
$(document).on("desktop_screen", function (e, data) {
	var desktop = data && data.desktop;
	if (!desktop || desktop.__hicom_avatar_wrapped) return;
	desktop.__hicom_avatar_wrapped = true;

	var hidden = [__("About"), __("Frappe Support")];
	var original = desktop.setup_avatar;
	desktop.setup_avatar = function () {
		var Dropdown = frappe.ui.Dropdown;
		frappe.ui.Dropdown = function (opts) {
			if (opts && Array.isArray(opts.options)) {
				opts.options = opts.options.filter(function (row) {
					return hidden.indexOf(row.label) === -1;
				});
			}
			return new Dropdown(opts);
		};
		try {
			return original.apply(this, arguments);
		} finally {
			frappe.ui.Dropdown = Dropdown;
		}
	};
});
