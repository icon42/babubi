# syntax=docker/dockerfile:1
#
# Babubi: gunicorn runs the app, WhiteNoise serves the static files and the app
# itself serves uploads, to signed-in users only. Put a reverse proxy that
# terminates TLS in front of it; see docs/setup/deployment.md.
#
# Data lives in /config, laid out as in the linuxserver Baby Buddy image
# (data/db.sqlite3, media/, .secretkey), so a volume from that image works
# as is.

FROM python:3.13-slim AS builder
COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.13-slim

# Babubi keeps its own version numbers; this records the Baby Buddy code it
# builds on. Update it with every merge from upstream.
LABEL babubi.upstream="babybuddy/babybuddy v2.11.0"

# Owner of /config. Match it to the owner of a bind-mounted host directory.
ARG UID=1000
ARG GID=1000
RUN groupadd --gid "$GID" babubi \
    && useradd --uid "$UID" --gid "$GID" --home-dir /app --no-create-home \
       --shell /usr/sbin/nologin babubi \
    && mkdir /config \
    && chown babubi:babubi /config

COPY --from=builder /venv /venv
# The code stays owned by root: the app user can read it but not change it.
COPY . /app
RUN ln -s /config/media /app/media

ENV PATH="/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=babubi.settings.base \
    DB_NAME=/config/data/db.sqlite3

WORKDIR /app
USER babubi
VOLUME /config
EXPOSE 8000
ENTRYPOINT ["/app/etc/docker-entrypoint.sh"]
