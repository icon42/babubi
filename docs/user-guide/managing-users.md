# Managing Users

## Creating a User

<video style="max-width: 320px;" autoplay controls loop muted playsinline>
  <source src="../../assets/videos/user_add.mp4" type="video/mp4">
</video>

## Changing User Settings

<video style="max-width: 320px;" autoplay controls loop muted playsinline>
  <source src="../../assets/videos/user_settings.mp4" type="video/mp4">
</video>

## Changing User Password

<video style="max-width: 320px;" autoplay controls loop muted playsinline>
  <source src="../../assets/videos/user_password.mp4" type="video/mp4">
</video>

## Permissions

![The user form with the permission matrix](../assets/images/user_permissions.png)

A user is either an **Administrator**, who can do everything, users and site
settings included, or an ordinary user whose access is set in the
**Permissions** table of the user form: one row per kind of entry (the
activities and the measurements), a **Read** column and a **Write** column.

- Read lets the user see that kind everywhere: its list, the dashboard cards,
  the timeline, the reports and the API.
- Write lets the user add, edit and delete entries of that kind, through the
  web interface and the API alike. Writing a kind implies reading it.
- The **All** box at the top of a column covers every kind, and the one in the
  corner covers both columns. An "All" is stored as such, not as the list of
  today's kinds, so a kind of entry added in a later version is covered too.
  While an "All" is ticked the boxes of its column are greyed out.

A few things follow from the table and are not shown in it:

- anyone who reads something can see the children and the tags;
- anyone who writes something can edit the children and create and assign
  tags;
- anyone who writes a timed kind (feeding, pumping, sleep or tummy time) can
  start, edit and finish timers, including timers that other users started.

The **Staff** box is separate: it opens user management and the site
settings, whatever the table says. Staff users who are not administrators
still need permissions of their own to see or record entries.

Permissions are Django's model permissions, so anything granted through the
database admin area at `/admin/`, including groups, counts as well. The user
form shows the user's effective permissions and, when saved, stores them as
the user's own.

!!! warning "Permissions are not limited to one child"

    A user with access to a kind of entry has it for every child on the
    instance. There is no per-child grant, and Babubi does not record which
    user created an entry.

To withdraw access, clear the **Active** checkbox on the user, or delete the
user. Subsequent web and API requests are denied, including requests using an
existing API key.

## Access Expiry

A user can be given an **Access expires** time in the user form, for example
for a babysitter who helps out for a weekend. From that time on, the user is
signed out, cannot sign in and cannot use the API, including with an existing
API key. The account itself is left unchanged: clearing or moving the time
restores access. Users cannot change their own expiry time.

## Creating a User from the Command Line

A user's type can be:

- Standard (default, an administrator who can access and make/edit any type of
  entry; permissions can be narrowed afterwards in the user form)
- Read only (can read every kind of entry but not make new entries)
- Staff (can access user management, site settings and the Database Admin area;
  available actions still depend on the account's permissions)

There are 2 ways you can create a user from the command line:

1. Passing user's password as an argument:

```shell
python manage.py createuser --username <username> --password <password>
```

This will create a user with the standard privileges.

2. Interactively setting user's password:

```shell
python manage.py createuser --username <username>
```

You will then be prompted to enter and confirm a password.

- If you want to create a user with read only privileges, pass in the `--read-only` flag:

```shell
python manage.py createuser --username <username> --password <password> --read-only
```

- If you want to create a user with the highest level of permission, you can append the `--is-staff` argument:

```shell
python manage.py createuser --username <username> --is-staff
```

- Another argument you can use with this command is `--email`

```shell
python manage.py createuser --username <username> --email <email>
```

- To get a list of supported commands:

```shell
python manage.py createuser --help
```
