# Application

## `DEBUG`

_Default:_ `False`

When in debug mode, Babubi will print much more detailed error information
for exceptions. This setting should be _False_ in production deployments.

See also [Django's documentation on the DEBUG setting](https://docs.djangoproject.com/en/5.0/ref/settings/#debug).

## `LANGUAGE_CODE`

_Default:_ `en-US`

Default language for new users, and the fallback for visitors whose browser
asks for no language Babubi has. Each user can still pick their own language in
their settings. The value must be one of the
languages Babubi ships, e.g. `ca` or `pt-BR`.

See also [Django's documentation on the LANGUAGE_CODE setting](https://docs.djangoproject.com/en/5.0/ref/settings/#language-code).

## `SUB_PATH`

_Default:_ `None`

If Babubi is hosted in a subdirectory of another server (e.g., `http://www.example.com/babubi`)
this must be set to the subdirectory path (e.g., `/babubi`) for correct handling of
application configuration.

Additional steps are required! See [Subdirectory configuration](../setup/subdirectory.md) for
details.

## `TIME_ZONE`

_Default:_ `UTC`

Default time zone for new users. Each user can still pick their own time zone in
their settings. The value must be a valid tz database name, e.g. `Europe/Paris`.

See also [Django's documentation on the TIME_ZONE setting](https://docs.djangoproject.com/en/5.0/ref/settings/#time-zone).
