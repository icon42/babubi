# Application

## `BRANDING_DIR`

_Default:_ `None` (`/config/branding` in the Docker image)

Directory with a deployment's own branding. Babubi uses each of these files when it is there, and its own otherwise:

- `logo.svg`: the logo on light backgrounds, such as the login page in the light theme.
- `logo-dark.svg`: the logo on dark backgrounds, such as the navigation bar. Without it, `logo.svg` is used there too.
- `icon.svg`: the square symbol, used in the navigation bar on small screens, on error pages and as the favicon.
- `custom.css`: extra styles, loaded after Babubi's own on every page. Target the themes with `[data-bs-theme="light"]` and `[data-bs-theme="dark"]`.

No other file in the directory is ever served. The files are public, since the login page needs them, and are picked up without a restart. App icons for phones (`apple-touch-icon.png` and the like) are not replaced.

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
