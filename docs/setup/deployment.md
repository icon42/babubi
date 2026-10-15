# Deployment

The default username and password for Babubi is `admin`/`admin`. For any
deployment, **log in and change the default password immediately**.

Many of Babubi's configuration settings can be controlled using environment
variables - see [Configuration](../configuration/intro.md) for detailed information.

## Docker

Babubi publishes a multi-architecture image (amd64 and arm64) at
`ghcr.io/icon42/babubi`, rebuilt every week so its base gets security fixes.
Use the following Docker Compose configuration as a template:

```yaml
services:
  babubi:
    image: ghcr.io/icon42/babubi:latest
    container_name: babubi
    environment:
      - ALLOWED_HOSTS=babubi.example.com
      - CSRF_TRUSTED_ORIGINS=https://babubi.example.com
      - SECURE_PROXY_SSL_HEADER=True
      - TIME_ZONE=Europe/Paris
      - LANGUAGE_CODE=en-US
    volumes:
      - /path/to/appdata:/config
    restart: unless-stopped
```

!!! warning

    The container speaks plain HTTP on port 8000 and is meant to sit behind a
    reverse proxy that terminates TLS (Traefik, Caddy, nginx, ...). Do not
    publish port 8000 to the internet: the proxy also shields the application
    server from slow or abusive clients. See [HTTPS/SSL configuration](ssl.md).

The `/config` volume holds the SQLite database (`data/db.sqlite3`), uploaded
files (`media/`) and a secret key generated on the first start
(`.secretkey`), unless `SECRET_KEY` is set. The app runs as user and group
`1000`; a bind-mounted directory must be writable by them. To use another
owner, build the image with `--build-arg UID=... --build-arg GID=...`.

Uploaded files such as child pictures are served by Babubi itself, and only
to signed-in users or API clients with a valid token.

To use your own logo, icon or extra CSS, put `logo.svg`, `logo-dark.svg`,
`icon.svg` or `custom.css` in `/config/branding/`. See
[`BRANDING_DIR`](../configuration/application.md#branding_dir).

Set `DATABASE_URL` (or the `DB_*` variables) to use PostgreSQL instead of
SQLite. See [Django's databases documentation](https://docs.djangoproject.com/en/5.0/ref/databases/)
for database requirements.

Every start applies pending database migrations before the app comes up.

### Migrating from Baby Buddy

Babubi can take over a Baby Buddy database. The `/config` layout matches the
[linuxserver Baby Buddy image](https://github.com/linuxserver/docker-babybuddy),
so stop Baby Buddy, **back up its `/config` directory**, and start Babubi on the
same volume. On its first start Babubi runs `migrate_from_babybuddy`, which
moves the tables, content types and migration records from the `babybuddy`
app label to `babubi`; later starts find nothing to move. Some Babubi
migrations cannot be undone, so the backup is the only way back.

### Running commands

Run administrative commands with `manage.py` inside the container; the
environment is already set up. For example:

```shell
docker exec -it babubi python manage.py --help
```

When `SECRET_KEY` comes from `/config/.secretkey`, pass it to the command:

```shell
docker exec -it babubi sh -c 'SECRET_KEY="$(cat /config/.secretkey)" python manage.py --help'
```

## Manual

There are many ways to deploy Babubi manually to any server/VPS. The basic
requirements are Python, a web server, an application server, and a database.

### Requirements

- Python 3.10+, pip, [pipx](https://pipx.pypa.io/), [pipenv](https://pipenv.pypa.io/)
- Web server ([nginx](http://nginx.org/), [Apache](http://httpd.apache.org/), etc.)
- Application server ([uwsgi](http://projects.unbit.it/uwsgi), [gunicorn](http://gunicorn.org/), etc.)
- Database (See [Django's databases documentation](https://docs.djangoproject.com/en/5.0/ref/databases/)).

### Example deployment

_This example assumes a 1 GB VPS instance with Ubuntu 24.04._ It uses Python 3.12,
nginx, uwsgi and sqlite. It should be sufficient for a few users (e.g., two parents
and any number of children).

1. Install system packages

   ```shell
   sudo apt-get install python3 python3-pip pipx nginx uwsgi uwsgi-plugin-python3 git libopenjp2-7-dev libpq-dev
   ```

2. Default python3 to python for this session

   ```shell
   alias python=python3
   ```

3. Install pipenv

   ```shell
   pipx ensurepath
   pipx install pipenv
   ```

4. Set up directories and files

   ```shell
   sudo mkdir /var/www/babubi
   sudo chown $USER:$(id -gn $USER) /var/www/babubi
   mkdir -p /var/www/babubi/data/media
   git clone --branch v1.0.0+bb.2.11.0 https://github.com/icon42/babubi.git /var/www/babubi/public
   ```

5. Move in to the application folder

   ```shell
   cd /var/www/babubi/public
   ```

6. Initiate and enter a Python environment with Pipenv locally.

   ```shell
   export PIPENV_VENV_IN_PROJECT=1
   pipenv install
   pipenv shell
   ```

7. Create a production settings file and set the `SECRET_KEY` and `ALLOWED_HOSTS` values

   ```shell
   cp babubi/settings/production.example.py babubi/settings/production.py
   editor babubi/settings/production.py
   ```

8. Initiate the application

   ```shell
   export DJANGO_SETTINGS_MODULE=babubi.settings.production
   python manage.py migrate
   ```

9. Set appropriate permissions on the database and data folder

   ```shell
   sudo chown -R www-data:www-data /var/www/babubi/data
   sudo chmod 640 /var/www/babubi/data/db.sqlite3
   sudo chmod 750 /var/www/babubi/data
   ```

10. Create and configure the uwsgi app

    ```shell
    sudo editor /etc/uwsgi/apps-available/babubi.ini
    ```

    Example config:

    ```ini
    [uwsgi]
    plugins = python3
    project = babubi
    base_dir = /var/www/babubi

    chdir = %(base_dir)/public
    virtualenv = %(chdir)/.venv
    module =  %(project).wsgi:application
    env = DJANGO_SETTINGS_MODULE=%(project).settings.production
    master = True
    vacuum = True
    ```

    See the [uWSGI documentation](http://uwsgi-docs.readthedocs.io/en/latest/)
    for more advanced configuration details.

    See [Subdirectory configuration](subdirectory.md) for additional configuration
    required if Babubi will be hosted in a subdirectory of another server.

11. Symlink config and restart uWSGI:

    ```shell
    sudo ln -s /etc/uwsgi/apps-available/babubi.ini /etc/uwsgi/apps-enabled/babubi.ini
    sudo service uwsgi restart
    ```

12. Create and configure the nginx server

    ```shell
    sudo editor /etc/nginx/sites-available/babubi
    ```

    Example config:

    ```nginx
    upstream babubi {
     server unix:///var/run/uwsgi/app/babubi/socket;
    }

    server {
     listen 80;
     server_name babubi.example.com;

     location / {
        uwsgi_pass babubi;
        include uwsgi_params;
     }
    }
    ```

    Do not add a `location` for `/media`: Babubi serves uploads itself, and only
    to signed-in users and API clients with a valid token. A web server serving
    that directory directly would hand child pictures to anyone with the URL.

    See the [nginx documentation](https://nginx.org/en/docs/) for more advanced
    configuration details.

    See [Subdirectory configuration](subdirectory.md) for additional configuration
    required if Babubi will be hosted in a subdirectory of another server.

13. Symlink config and restart NGINX:

    ```shell
    sudo ln -s /etc/nginx/sites-available/babubi /etc/nginx/sites-enabled/babubi
    sudo service nginx restart
    ```

14. That's it (hopefully)!

See [HTTPS/SSL configuration](ssl.md) for information on how to secure Babubi.
