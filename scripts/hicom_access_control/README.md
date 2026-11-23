# Hicom Subscription & Access Control

An internal Hicom control, not something a client asked for. It is installed per site.

- **User limit.** `Hicom Subscription Settings` caps how many desk users a client can have. Only System Manager (Hicom) can open it.
- **User Manager role.** A client can create, edit, disable and delete their own users (disabling or deleting frees a seat, re-enabling takes it back) and assign them Role Profiles. They can never give System Manager, or any other protected role, and they cannot see or change Hicom's System Manager accounts.

Everything is created as ordinary site records: a custom Module Def "Hicom", Custom DocTypes, a Role, Custom DocPerms, Server Scripts and Client Scripts. It can all be adjusted in the UI on production. This folder is **not app code**. hicom16 doesn't need to be installed on the site.

## Files

| File | What it is |
|---|---|
| `install.py` | Creates everything on one site. Safe to re-run. |
| `verify.py` | 28 end-to-end checks acting as a User Manager. Everything is rolled back afterwards. |
| `server_scripts/*.py` | Bodies of the Server Scripts, loaded by `install.py`. |
| `client_scripts/*.js` | Bodies of the Client Scripts, loaded by `install.py`. |

## What gets created

| Record | Purpose |
|---|---|
| DocType `Hicom Subscription Settings` (Single) | Enable limit, Maximum Users (0 = no limit), Users Not Counted, Roles Not Counted, Protected Roles |
| DocTypes `Hicom Seat Exempt User`, `Hicom Seat Exempt Role`, `Hicom Protected Role` | Child tables for the lists above |
| Role `User Manager` | User: read/write/create/delete/report at level 0, read/write at level 1. Role Profile and Module Profile: read only |
| Server Script `Hicom - User Access Guard` | User, Before Save. A non-System Manager can only give access through Role Profiles, can never give a protected role, and cannot change an account that holds one |
| Server Script `Hicom - User Seat Limit` | User, Before Save. Blocks a new or newly counted desk user once the limit is reached, including a new user made from Quick Entry that holds no role yet. Portal sign-ups (Guest) are not affected. This applies to System Manager too |
| Server Scripts `Hicom - User Delete Guard` / `Hicom - User Rename Guard` | Protected accounts cannot be deleted or renamed by a non-System Manager |
| Server Script `Hicom - User List Filter` | Permission Query. Hides protected accounts from the User list for non-System Managers |
| Server Script `Hicom - User Seat Info` | API `hicom_user_seat_info`. Returns seat usage and the Role Profiles a User Manager may pick |
| Client Script `Hicom - User Form` | For non-System Managers: filters the Role Profile picker to profiles without a protected role, and shows "7 of 10 users used" on a new user. The form layout (role editor, Allow Modules, User Type) is left as core shows it |
| Client Script `Hicom - Subscription Settings Form` | Shows current usage on the settings form |

**Who counts as a seat:** every **enabled** System User (disabled users do not count), except:

- Administrator and Guest
- anyone in Users Not Counted
- anyone holding a role in Roles Not Counted, which is seeded with System Manager

Portal (Website) users never count.

## Run on dev

```bash
cd ~/Dev/benchv16/sites
../env/bin/python ../apps/hicom16/scripts/hicom_access_control/install.py --site bp.localhost
../env/bin/python ../apps/hicom16/scripts/hicom_access_control/verify.py --site bp.localhost
```

Re-running `install.py` only adds what is missing. If a script body on the site differs from the file here, it is reported as SKIPPED. Pass `--update-scripts` to overwrite it. This is deliberate, so edits made in the UI on production aren't lost by accident.

## Rollout to a client on the VPS (needs Bry's go-ahead per site)

1. Confirm `server_script_enabled: 1` in that bench's `common_site_config.json`. Without it the guards and the limit do nothing, and the installer prints a warning.
2. Copy this folder into the backend container, then run it from the container's `sites` directory:
   ```bash
   docker cp hicom_access_control <container>:/home/frappe/frappe-bench/
   docker exec -it <container> bash -c "cd /home/frappe/frappe-bench/sites && ../env/bin/python ../hicom_access_control/install.py --site <site>"
   ```
3. Open **Hicom Subscription Settings**, tick Enable User Limit, and set Maximum Users to the client's package.
4. Create the Role Profiles the client may assign. Any profile containing a Protected Role is automatically hidden from the User Manager.
5. Take System Manager off the client's own accounts. Give their admin the **User Manager** role plus the Role Profile they need for daily work.
6. Optionally run `verify.py --site <site>`. It rolls everything back, so it is safe on production.

## Known limits

- A User Manager can still **read** a protected account if they open its exact URL. The list, link searches and reports hide it, and every write is blocked. Blocking reads too would need a `has_permission` hook, which means app code.
- Changes made with `frappe.db.set_value` or direct SQL skip Server Scripts. Only System Manager or code can do that.
- A limit lowered below current usage blocks nothing retroactively. It only stops new or newly counted users.
