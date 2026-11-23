// Hicom - Subscription Settings Form  (Hicom Subscription Settings / Form)
// Shows the current seat usage next to the limit.

frappe.ui.form.on("Hicom Subscription Settings", {
	refresh(frm) {
		frappe.call("hicom_user_seat_info").then((r) => {
			const info = r.message;
			const limit = info.limit_on && info.limit ? info.limit : __("no limit");
			frm.get_field("seat_usage").$wrapper.html(
				`<div class="text-muted">${__("Users counted now")}: <b>${info.used}</b> / ${limit}</div>`
			);
		});
	},
});
