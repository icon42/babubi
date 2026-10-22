# Security

## `ALLOWED_HOSTS`

_Default:_ `""` (empty)

Set this variable to a single host or comma-separated list of hosts.
This should _always_ be set to a specific host or hosts in production deployments.

Do not include schemes ("http" or "https") with this setting.

**Example value**

    baby.example.test, baby.example2.test

**See also**

- [Django's documentation on the ALLOWED_HOSTS setting](https://docs.djangoproject.com/en/5.0/ref/settings/#allowed-hosts)
- [`CSRF_TRUSTED_ORIGINS`](#csrf_trusted_origins)
- [`SECURE_PROXY_SSL_HEADER`](#secure_proxy_ssl_header)

## `CORS_ALLOWED_ORIGINS`

_Default:_ `""` (no cross-origin requests allowed)

Set this variable to a single origin or comma-separated list of origins. Include schemes
("http" or "https") and any non-default ports in each origin.

This allows cross-origin requests to the API from the specified origins.

**Example value**

    https://other-domain.example.com, http://localhost:8888

**See also**

- [MDN article on CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Making cross origin requests using fetch()](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch#making_cross-origin_requests)

## `CSRF_COOKIE_SECURE`

_Default:_ `False`

If this is set to `True`, the browser CSRF cookie will be marked as "secure", which instructs the browser to only send the cookie over an HTTPS connection (never HTTP).

**See also**

- [Django's documentation on the `CSRF_COOKIE_SECURE` setting](https://docs.djangoproject.com/en/5.0/ref/settings/#csrf-cookie-secure)

## `CSRF_TRUSTED_ORIGINS`

_Default:_ `None`

If Babubi is behind a proxy, you may need add all possible origins to this setting
for form submission to work correctly. Separate multiple origins with commas.

Each entry must contain both the scheme (http, https) and fully-qualified domain name.

**Example value**

    https://baby.example.test,http://baby.example2.test,http://babybudy

**See also**

- [Django's documentation on the `CSRF_TRUSTED_ORIGINS` setting](https://docs.djangoproject.com/en/5.0/ref/settings/#std:setting-CSRF_TRUSTED_ORIGINS)
- [`ALLOWED_HOSTS`](#allowed_hosts)
- [`SECURE_PROXY_SSL_HEADER`](#secure_proxy_ssl_header)

## `LOGIN_METHODS`

_Default:_ `password`

How users log in to the web interface: `password`, `oidc` or both, separated by a comma.

- `password`: the username and password form.
- `oidc`: a button that logs in through an OpenID Connect provider, configured with the `OIDC_*` variables below.
- `password,oidc`: the form and, below it, the button.
- `oidc,password`: the button and, below it, the form.

With both, the login page follows the order of the value, and the first method gets the primary button.

With `oidc` alone, Babubi accepts no passwords on the web: the login form, the admin login, the API browser login and password reset are all turned off. API tokens keep working with any value.

Babubi never creates users from OIDC: add each user first. A provider account meets its Babubi user in one of two ways, and from then on the two stay linked by the provider's `sub` claim:

- At the first OIDC login, by the user's email, which the provider must report as verified (`email_verified`), or by the username when [`OIDC_MATCH_BY`](#oidc_match_by) says so. Exactly one user must match, ignoring case.
- From the user settings page, where a user logged in with a password can link the provider account directly, whatever its claims say, and unlink it again while password login stays available.

Inactive users and users whose access has expired are turned away.

Register Babubi with the provider as a confidential client with these addresses:

- Redirect URI: `https://<babubi host>/oidc/complete/oidc/`
- Back-channel logout URI (optional): `https://<babubi host>/oidc/logout/backchannel/`

With back-channel logout, the provider tells Babubi when a user's session ends there, and every Babubi session of that user ends too. Babubi follows OpenID Connect Back-Channel Logout 1.0 and needs the `sub` claim in the logout token.

Behind a reverse proxy that terminates HTTPS, set [`SECURE_PROXY_SSL_HEADER`](#secure_proxy_ssl_header) so the redirect URI Babubi sends uses `https`.

If the provider is down and nobody has a session, switch to `password,oidc` and restart to log in with a password.

**Example value**

    oidc

**See also**

- [`OIDC_ENDPOINT`](#oidc_endpoint)
- [`SESSION_COOKIE_AGE`](#session_cookie_age)

## `OIDC_CLIENT_ID`

_Default:_ `""` (empty)

The client ID Babubi has at the OpenID Connect provider. Required when [`LOGIN_METHODS`](#login_methods) includes `oidc`.

## `OIDC_CLIENT_SECRET`

_Default:_ `""` (empty)

The client secret Babubi has at the OpenID Connect provider. Required when [`LOGIN_METHODS`](#login_methods) includes `oidc`.

## `OIDC_ENDPOINT`

_Default:_ `""` (empty)

The issuer URL of the OpenID Connect provider, without `/.well-known/openid-configuration`. Babubi reads the rest of the provider's configuration from there. Required when [`LOGIN_METHODS`](#login_methods) includes `oidc`.

**Example value**

    https://idp.example.com

## `OIDC_MATCH_BY`

_Default:_ `email`

How a provider account that logs in for the first time finds its Babubi user:

- `email`: the `email` claim must equal the user's email, and the provider must report it as verified (`email_verified`). A user without an email cannot log in through OIDC until one is set, or the account is linked from the user settings page.
- `username`: the `preferred_username` claim must equal the username. Only safe with a provider where users cannot choose or change their own username: anyone who can register the username of a Babubi user at the provider would log in as that user.

A user matched once stays linked by the `sub` claim, so changing this setting later only affects users not linked yet.

## `OIDC_PROVIDER_NAME`

_Default:_ `None`

The provider name shown on the login button, as in "Log in with Example ID". Without it, the button reads "Log in with single sign-on".

## `OIDC_SCOPES`

_Default:_ `openid profile email`

The scopes Babubi requests from the OpenID Connect provider, separated by spaces. The `email` scope carries the `email` and `email_verified` claims, and `profile` the `preferred_username` claim, which [`OIDC_MATCH_BY`](#oidc_match_by) chooses between.

## `PROXY_HEADER`

_Default:_ `HTTP_REMOTE_USER`

Sets the header to read the authenticated username from when
`REVERSE_PROXY_AUTH` has been enabled.

Babubi modifies headers in the HTTP request; HTTP headers in the request have all characters converted to uppercase, replacing any hyphens with underscores and adding an HTTP\_ prefix to the name. For example `X-Auth-User` would be converted to `HTTP_X_AUTH_USER`.

**Example value**

    // For header key X-Auth-User
    HTTP_X_AUTH_USER

**See also**

- [Django's documentation on the `REMOTE_USER` authentication method](https://docs.djangoproject.com/en/5.0/howto/auth-remote-user/)
- [Django's documentation on the request.META object](https://docs.djangoproject.com/en/5.0/ref/request-response/#django.http.HttpRequest.META)
- [`REVERSE_PROXY_AUTH`](#reverse_proxy_auth)

## `REVERSE_PROXY_AUTH`

_Default:_ `False`

Enable use of `PROXY_HEADER` to pass the username of an authenticated user.
This setting should _only_ be used with a properly configured reverse proxy to
ensure the headers are not forwarded from sources other than your proxy.

**See also**

- [`PROXY_HEADER`](#proxy_header)

## `SECRET_KEY`

_Default:_ `None`

A random, unique string must be set as the "secret key" before Babubi can
be deployed and run.

See also [Django's documentation on the SECRET_KEY setting](https://docs.djangoproject.com/en/5.0/ref/settings/#secret-key).

## `SECURE_PROXY_SSL_HEADER`

_Default:_ `None`

If Babubi is behind a proxy, you may need to set this to `True` in order to
trust the `X-Forwarded-Proto` header that comes from your proxy, and any time
its value is "https". This guarantees the request is secure (i.e., it originally
came in via HTTPS).

**See also**

- [Django's documentation on the SECURE_PROXY_SSL_HEADER setting](https://docs.djangoproject.com/en/5.0/ref/settings/#secure-proxy-ssl-header)
- [`ALLOWED_HOSTS`](#allowed_hosts)
- [`CSRF_TRUSTED_ORIGINS`](#csrf_trusted_origins)

## `SESSION_COOKIE_AGE`

_Default:_ `1209600` (two weeks)

How long a login lasts, in seconds. Babubi renews the session once a day while it is in use, so an active user stays logged in.

**Example value**

    2592000

**See also**

- [Django's documentation on the `SESSION_COOKIE_AGE` setting](https://docs.djangoproject.com/en/5.0/ref/settings/#session-cookie-age)

## `SESSION_COOKIE_SECURE`

_Default:_ `False`

If this is set to `True`, the browser session cookie will be marked as "secure", which instructs the browser to only send the cookie over an HTTPS connection (never HTTP).

**See also**

- [Django's documentation on the `SESSION_COOKIE_SECURE` setting](https://docs.djangoproject.com/en/5.0/ref/settings/#session-cookie-secure)
