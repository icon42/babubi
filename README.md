<img src="babubi/static_src/logo/logo.svg" height="80" alt="Babubi">

# Babubi

[![License](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg)](LICENSE)
[![CI Status](https://github.com/icon42/babubi/actions/workflows/ci.yml/badge.svg)](https://github.com/icon42/babubi/actions/workflows/ci.yml)
[![Support: none](https://img.shields.io/badge/support-none-lightgrey.svg)](SUPPORT.md)

Babubi helps caregivers track sleep, feedings, diaper changes, tummy time and more, to learn about and predict a baby's needs with less guesswork.

Babubi is a fork of [Baby Buddy](https://github.com/babybuddy/babybuddy). It starts from Baby Buddy's tagged releases and adds its own packaging and changes on top. It is not affiliated with the Baby Buddy project.

![Babubi desktop view](screenshot.png)

![Babubi mobile views](screenshot_mobile.png)

## How Babubi differs from Baby Buddy

- **Own container image**, published at `ghcr.io/icon42/babubi` for amd64 and arm64 and rebuilt every week so its base gets security fixes. It runs as an unprivileged user.
- **Private uploads.** Child pictures and other uploads are served only to signed-in users and to API clients with a valid token, never to anyone who just has the URL.
- **Locale defaults from the environment.** `LANGUAGE_CODE` and `TIME_ZONE` set the defaults for new users; without them Babubi uses Baby Buddy's (`en-US`, `UTC`).
- **Light, dark and automatic themes** in Babubi's colours, chosen by each user, with the browser's preference as the default.
- **Your own logo and styles** without rebuilding the image: drop `logo.svg`, `icon.svg` or `custom.css` into `/config/branding/` (see [`BRANDING_DIR`](docs/configuration/application.md#branding_dir)).
- **Drop-in migration from Baby Buddy.** Its `/config` volume matches the linuxserver Baby Buddy image, and the first start moves the database over to Babubi on its own.

## Getting started

Babubi runs as a container behind a reverse proxy that terminates TLS. A minimal Docker Compose service:

```yaml
services:
  babubi:
    image: ghcr.io/icon42/babubi:1
    environment:
      - ALLOWED_HOSTS=babubi.example.com
      - CSRF_TRUSTED_ORIGINS=https://babubi.example.com
      - SECURE_PROXY_SSL_HEADER=True
    volumes:
      - /path/to/appdata:/config
    restart: unless-stopped
```

The first start creates the user `admin` with the password `admin`: log in and change it immediately. See [Deployment](docs/setup/deployment.md) for the full setup, including how to move an existing Baby Buddy installation to Babubi.

## Versions

Babubi has its own version numbers and follows [Semantic Versioning](https://semver.org/). Each release tag also names the Baby Buddy release it builds on, as build metadata: `v1.0.0+bb.2.11.0` is Babubi 1.0.0 on top of Baby Buddy 2.11.0. The same Baby Buddy release can carry several Babubi versions, and a new Baby Buddy release always comes in with a new Babubi version.

Container tags hold the Babubi version only (`1.0.0`, `1.0`, `1` and `latest`), since they cannot contain a `+`. The image label `babubi.upstream` records the Baby Buddy release.

## Documentation

The documentation lives in the [`docs`](docs/index.md) directory of this repository:

- [Deployment](docs/setup/deployment.md), [HTTPS/SSL](docs/setup/ssl.md), [reverse proxies](docs/setup/proxy.md) and [subdirectories](docs/setup/subdirectory.md)
- [Configuration](docs/configuration/intro.md) through environment variables
- [User guide](docs/user-guide/getting-started.md)
- [API](docs/api.md), [import and export](docs/import-export.md) and the [MCP server](docs/mcp.md)
- [Contributing](docs/contributing/pull-requests.md), including [translations](docs/contributing/translation.md)

## Languages

Each user picks their language in their settings (`/user/settings/`); `LANGUAGE_CODE` sets the default. Translations come from Baby Buddy's translators and are edited in the `.po` files under [`locale`](locale); see [Translation](docs/contributing/translation.md).

Available languages: Brazilian Portuguese, Catalan, Chinese (simplified), Chinese (traditional), Chinese (Taiwan), Croatian, Czech, Danish, Dutch, English (U.K.), English (U.S., the base language), Finnish, French, German, Hebrew, Hungarian, Italian, Japanese, Korean, Norwegian Bokmål, Polish, Portuguese, Russian, Serbian, Spanish, Swedish, Turkish and Ukrainian.

## Works with the Baby Buddy ecosystem

Babubi keeps Baby Buddy's REST API unchanged, so apps and integrations built for Baby Buddy are expected to work with it. They are made by others for Baby Buddy, and none of them has been tested with Babubi.

### AI

- [babubi-mcp](https://github.com/icon42/babubi-mcp): a [Model Context Protocol](https://modelcontextprotocol.io) server for logging and querying Babubi data with AI assistants, forked from babybuddy-mcp alongside Babubi. See the [MCP documentation](docs/mcp.md).

### Smart home

- [Baby Buddy Home Assistant integration](https://github.com/jcgoette/baby_buddy_homeassistant): monitor and use Babubi from Home Assistant
- [Baby Buddy Alexa skill](https://github.com/babybuddy/babybuddy-alexa-skill)

### Hardware

- [Bottle Scale for Baby Buddy and Home Assistant with ESPHome](https://github.com/sfgabe/OITProjects/tree/master/BabyBuddy_ESP_HASS)
- [Quick Entry Keypad (ESP8266)](https://github.com/sfgabe/OITProjects/tree/master/Baby_Buddy_Keypad)
- [Baby Buddy Keypad (ESP32)](https://github.com/jeroenterheerdt/Baby-Buddy-Keypad)
- [BabyScout](https://github.com/MikeSchapp/BabyScout): keypad for recording diaper changes, feedings and sleep
- [BabyPod](https://www.printables.com/model/872095-babypod-a-remote-control-for-baby-buddy-for-new-pa): a remote control for new parents (sources: [hardware](https://github.com/skjdghsdjgsdj/babypod-hardware), [software](https://github.com/skjdghsdjgsdj/babypod-software/))
- [MatrixPortal Baby Buddy](https://github.com/skjdghsdjgsdj/matrixportal-babybuddy)

### Mobile

- [Baby Buddy Companion for iOS](https://apps.apple.com/app/id6788966667) ([source](https://github.com/kguy18/babybuddyios/))
- [Baby Buddy for Android](https://play.google.com/store/apps/details?id=eu.pkgsoftware.babybuddywidgets) ([source](https://github.com/babybuddy/babybuddy-for-android))
- [iOS shortcuts](https://github.com/babybuddy/babybuddy/discussions/300)
- [Convert exported data from the "Baby tracker - feeding, sleep and diaper" app](https://github.com/babybuddy/babybuddy/discussions/424)

### Other

- [Grafana dashboard](https://github.com/babybuddy/babybuddy/discussions/607)
- Newborn parenting software series (API, buttons, LCD information screen): [part 1](https://lutzky.net/2021/10/03/software-parenting-1/), [part 2](https://lutzky.net/2021/10/05/software-parenting-2/), [part 3](https://lutzky.net/2021/10/10/software-parenting-3/)
- [Example custom TypeScript frontend](https://github.com/jkjustjoshing/maddie-buddy), based on [Remix](https://remix.run/)

## Support

Babubi is offered as is, without support; see [SUPPORT.md](SUPPORT.md).

## Reporting vulnerabilities

See [SECURITY.md](SECURITY.md).

## License and credits

Babubi is released under the [BSD 2-Clause License](LICENSE), like Baby Buddy, and keeps the copyright notice of Baby Buddy's contributors. Almost all of Babubi's code, design and translations is their work.
