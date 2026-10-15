# Deployment

The default username and password for Babubi is `admin`/`admin`. For any
deployment, **log in and change the default password immediately**.

Many of Babubi's configuration settings can be controlled using environment
variables - see [Configuration](../configuration/intro.md) for detailed information.

## Docker

Babubi relies on the [LinuxServer.io](https://www.linuxserver.io/) community
for a multi-architecture container with strong support. See
[linuxserver/docker-babubi](https://github.com/linuxserver/docker-babybuddy)
for detailed information about the container or use the following Docker Compose
configuration as a template to get started quickly:

```yaml
version: "2.1"
services:
  babubi:
    image: lscr.io/linuxserver/babubi
    container_name: babubi
    volumes:
      - /path/to/appdata:/config
    ports:
      - 8000:8000
    restart: unless-stopped
```

See [Django's databases documentation](https://docs.djangoproject.com/en/5.0/ref/databases/) for database requirements.

See [HTTPS/SSL configuration](ssl.md) for information on how to secure Babubi.

### Running commands

Run administrative commands with the `/app/www/public/manage.py` script. Set
the environment variables `DJANGO_SETTINGS_MODULE` and `SECRET_KEY` before
running commands. For example:

```shell
docker exec -it babubi /bin/bash
export DJANGO_SETTINGS_MODULE="babubi.settings.base"
export SECRET_KEY="$(cat /config/.secretkey)"
cd /app/www/public
python manage.py --help
```

Note: the container name (`babubi`) and secret key location
(`/config/.secretkey`) may differ depending on the container configuration.
Refer to the running containers configuration for these values.

## Home Assistant

[Home Assistant](https://www.home-assistant.io/) is an open source home automation tool
that can be used to host and control Babubi. An existing Home Assistant installation
is required to use this method.

See the community-maintained [Babubi Home Assistant Addon](https://github.com/OttPeterR/addon-babybuddy)
for installation instructions and then review the
community-maintained [Babubi Home Assistant integration](https://github.com/jcgoette/baby_buddy_homeassistant)
for added integrations with the base Home Assistant system.

See
also [How to Setup Babubi in Home Assistant](https://smarthomescene.com/guides/how-to-setup-baby-buddy-in-home-assistant/)
from Smart Home Scene for more detailed installation and configuration instructions.

## Digital Ocean

!!! info

    The Digital Ocean deployment and link URLs include referal codes. All referral funds receieved are treated as donations to Babubi.

There are two ways to deploy Babubi to Digital Ocean -- as a droplet from a marketplace image or as an app.

The **marketplace image** is the cheaper option ($6/month), but may require more manual configuration depending on desired features and is limited to the latest release the marketplace image has been approved for.

The **app** can be de deployed from any tag or the main branch and can be managed in the Digital Ocean console via environment variables, but it costs at least $12/month.

### Create droplet

**Cost**: $6+/month

Use the button below to create a new droplet using the Babubi marketplace image.

Access and configuration instructions will be provided after the droplet has been started and configured by the image.

[![Create Droplet](../assets/images/do-btn-blue.svg)](https://marketplace.digitalocean.com/apps/baby-buddy?refcode=dd79e4cfd7b6&action=deploy)

### Create app

**Cost**: $12+/month

Use the button below to start a new deploy to [Digital Ocean](https://www.digitalocean.com/?refcode=dd79e4cfd7b6&utm_campaign=Referral_Invite&utm_medium=Referral_Program&utm_source=badge).

Modify the app environment variables during the build configuration and set the `SECRET_KEY` value to something random
and unique. Digital Ocean's automatic secret generator does not work with Babubi.

[![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/babybuddy/babybuddy/tree/master&refcode=dd79e4cfd7b6)

## Clever Cloud

To deploy on [Clever Cloud](https://www.clever-cloud.com), log in to your
[Clever Cloud console](https://console.clever-cloud.com/), create a Python
application, link it to a PostgreSQL addon and optionally a Cellar S3 Storage
addon (only if you want file storage for child picture in particular).
Then make sure to set the following environment variables in your Python
application before pushing the babubi source code:

```shell
CC_PYTHON_BACKEND=uwsgi
CC_PYTHON_MANAGE_TASKS=migrate
CC_PYTHON_MODULE=babubi.wsgi:application
DJANGO_SETTINGS_MODULE=babubi.settings.clever-cloud
SECRET_KEY=<CHANGE TO SOMETHING RANDOM>
AWS_STORAGE_BUCKET_NAME=<DESIRED BUCKET NAME> # only if file storage is needed
```

See [Configuration](../configuration/intro.md) for other environment variables available
for your instance of babubi.

After that, you just have to push babubi code repository to the Git
deployment URL of your Clever Cloud Python application.

## GCP Cloud Run

Babubi can be hosted serverless in GCP Cloud Run using configuration provided at
`terraform/gcp-cloud-run`. The configuration scales down to zero for cost-effectiveness.
With this approach initial requests to the service after a long period will be slow but
subsequent requests will be much faster.
A [billing account](https://cloud.google.com/billing/docs/how-to/create-billing-account)
mut be configured in GCP to use the configuration.

The terraform code isn't production ready and is meant to be a good way of getting started.
No state storage is configured. See [storage options](https://cloud.google.com/run/docs/storage-options)
for information about how to configure persistent storage.

Run `terraform init` from the configuration directory to get started:

```shell
git clone https://github.com/babybuddy/babybuddy.git
cd babubi/terraform/gcp-cloud-run
terraform init
terraform apply -var project_id=<project-id> -var project_name=<project-name> -var billing_account=<billing-account-id>
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
   git clone https://github.com/babybuddy/babybuddy.git /var/www/babubi/public
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

     location /media {
        alias /var/www/babubi/data/media;
     }
    }
    ```

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
