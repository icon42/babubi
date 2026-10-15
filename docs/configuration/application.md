# Application

## `DEBUG`

_Default:_ `False`

When in debug mode, Babubi will print much more detailed error information
for exceptions. This setting should be _False_ in production deployments.

See also [Django's documentation on the DEBUG setting](https://docs.djangoproject.com/en/5.0/ref/settings/#debug).

## `SUB_PATH`

_Default:_ `None`

If Babubi is hosted in a subdirectory of another server (e.g., `http://www.example.com/babubi`)
this must be set to the subdirectory path (e.g., `/babubi`) for correct handling of
application configuration.

Additional steps are required! See [Subdirectory configuration](../setup/subdirectory.md) for
details.
