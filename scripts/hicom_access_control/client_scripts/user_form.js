// Hicom - User Form  (User / Form)
//
// For anyone who is not System Manager (a client's User Manager):
//   - the Role Profile picker offers only profiles that grant no protected role
//   - a new user shows how many user seats are used
// The form layout itself (role editor, Allow Modules, User Type) is left as core shows it.
// Cosmetic only - the rules are enforced by the Hicom Server Scripts on User.

function hicom_is_system_manager() {
	return frappe.user.has_role("System Manager");
}

frappe.ui.form.on("User", {
	setup(frm) {
		frm.set_query("role_profiles", () => {
			if (hicom_is_system_manager()) return {};
			const allowed = frm.hicom_seat_info?.allowed_role_profiles || [];
			return { filters: { name: ["in", allowed.length ? allowed : [""]] } };
		});
	},

	onload(frm) {
		frappe.call("hicom_user_seat_info").then((r) => {
			frm.hicom_seat_info = r.message;
			frm.trigger("hicom_seat_intro");
		});
	},

	refresh(frm) {
		frm.trigger("hicom_seat_intro");
	},

	hicom_seat_intro(frm) {
		const info = frm.hicom_seat_info;
		if (!frm.is_new() || !info || !info.limit_on || !info.limit) return;
		const full = info.used >= info.limit;
		frm.set_intro(
			__("{0} of {1} users used.", [info.used, info.limit]) +
				(full ? " " + __("The limit is reached - contact Hicom to add more users.") : ""),
			full ? "red" : "blue"
		);
	},
});
