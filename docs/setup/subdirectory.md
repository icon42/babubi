# Subdirectory

Babubi's default configuration assumes deployment in to the root of a web server.
Some additional configuration is required to install Babubi in a subdirectory of a
server instead (e.g., to `http://www.example.com/babubi`).

## Minimum version

Babubi added full support for subdirectory installing in version **1.10.2**. While
it is still possible to do a subdirectory installation in older versions of Babubi
it is not recommended.

## [`SUB_PATH`](../configuration/application.md#sub_path)

Set this environment variable to the subdirectory of the Babubi installation. E.g.,
`SUB_PATH=/babubi` if the desired URL is `http://www.example.com/babubi`).

## uWSGI + NGINX configuration

When using uWSGI and NGINX (as in the [example deployment](deployment.md#example-deployment))
the following configurations are required.

_Assume the subdirectory `babubi` for configuration change examples below but this
can be anything includes multiple subdirectories (e.g., `/my/apps/babubi`). Other
paths used in these examples also assume a configuration based on the
[example deployment](deployment.md#example-deployment)._

### uWSGI

In the app configuration replace the `module` declaration with a `mount` declaration and
add the `manage-script-name` declaration and [`SUB_PATH`](../configuration/application.md#sub_path)
environment variable to the `[uwsgi]` configuration block.

```diff
- module = %(project).wsgi:application
+ mount = /babubi=%(project).wsgi:application
+ manage-script-name = true
+ env = SUB_PATH=/babubi
```

### NGINX

Alter the NGINX `server` configuration to include the desired subdirectory path in the
app (Babubi root) and media `location` declarations _and_ add a new declaration for
the static `location`.

```diff
-    location / {
+    location /babubi {
```

```diff
+    location /babubi/static {
+        alias /var/www/babubi/public/static;
+    }
```

```diff
-    location /media {
+    location /babubi/media {
```
