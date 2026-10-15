<img src="babubi/static_src/logo/icon.png" height="150" align="left">

# Babubi

[![License](https://img.shields.io/badge/License-BSD%202--Clause-orange.svg)](https://opensource.org/licenses/BSD-2-Clause)
[![Gitter](https://img.shields.io/gitter/room/nwjs/nw.js.svg)](https://gitter.im/babybuddy/Lobby)
[![CI Status](https://github.com/babybuddy/babybuddy/actions/workflows/ci.yml/badge.svg)](https://github.com/babybuddy/babybuddy/actions/workflows/ci.yml)
[![Coverage Status](https://coveralls.io/repos/github/babybuddy/babybuddy/badge.svg?branch=master)](https://coveralls.io/github/babybuddy/babybuddy?branch=master)
[![Open in GitHub Codespaces ready-to-code](https://img.shields.io/badge/Codespace-ready--to--code-blue?logo=github)](https://codespaces.new/babybuddy/babybuddy?quickstart=1)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A buddy for babies! Helps caregivers track sleep, feedings, diaper changes,
tummy time and more to learn about and predict baby's needs without (_as much_)
guess work.

![Babubi desktop view](screenshot.png)

![Babubi mobile views](screenshot_mobile.png)

## 👾 Demo

A [demo of Babubi](https://demo.baby-buddy.net) is available. The demo instance
resets every hour. Login credentials are:

- Username: `admin`
- Password: `admin`

## 📘 Documentation

Visit [https://docs.baby-buddy.net](https://docs.baby-buddy.net) for full documentation.

### Additional documentation

- [Security](/SECURITY.md)
- [License](/LICENSE) (BSD-2 Clause)

## 🗺️ Languages

Babubi is available in a variety of languages thanks to the efforts of numerous
translators. Language can be set on a per-user basis from the user settings page
(`/user/settings/`). See [Contributing](https://docs.baby-buddy.net/contributing/translation/)
for information about how to create/update translations.

### Available languages

:brazil: Brazilian Portuguese, :es: Catalan, :cn: Chinese (simplified), :hong_kong: Chinese (traditional), :taiwan: Chinese (Taiwan), :croatia: Croatian, :czech_republic: Czech, :denmark: Danish, :netherlands: Dutch, :uk: English (U.K.), :us: English (U.S.) (base), :finland: Finnish, :fr: French, :de: German, :israel: Hebrew, :hungary: Hungarian, :it: Italian, :jp: Japanese, :kr: Korean, :norway: Norwegian Bokmål, :poland: Polish, :portugal: Portuguese, :ru: Russian, :serbia: Serbian, :mexico: :es: Spanish, :sweden: Swedish, :tr: Turkish, :ukraine: Ukrainian

## 🌐 Babubi on the Web

This is a non-exhaustive list of neat projects and blog posts that either extend
or use Babubi in fun ways. If you have a project to share please open a PR
adding it here or reach out via GitHub Issues or Discussions or on Gitter!

### AI

- [Babubi MCP server](https://github.com/babybuddy/babybuddy-mcp) - A [Model Context Protocol](https://modelcontextprotocol.io) server for logging and querying Babubi data with AI assistants. See the [MCP documentation](https://docs.baby-buddy.net/mcp/).

### Smart home

- [Home Assistant Addon](https://github.com/OttPeterR/addon-babybuddy) (host Babubi on Home Assistant)
- [Home Assistant integration](https://github.com/jcgoette/baby_buddy_homeassistant) (monitor and use Babubi from Home Assistant)
- [How to Setup Babubi in Home Assistant](https://smarthomescene.com/guides/how-to-setup-baby-buddy-in-home-assistant/)
- [Babubi and Home Assistant](https://martinnoah.com/babybuddy-and-home-assistant.html)
- [Alexa skill](https://github.com/babybuddy/babybuddy-alexa-skill)

### Hardware

- [Bottle Scale for Babubi and Home Assistant with ESPHome](https://github.com/sfgabe/OITProjects/tree/master/BabyBuddy_ESP_HASS)
- [Quick Entry Keypad (ESP8266)](https://github.com/sfgabe/OITProjects/tree/master/Baby_Buddy_Keypad)
- [Babubi Keypad (ESP32)](https://github.com/jeroenterheerdt/Baby-Buddy-Keypad)
- [BabyScout](https://github.com/MikeSchapp/BabyScout) - Keypad for recording diaper changes, feedings and sleep to Babubi
- [BabyPod](https://www.printables.com/model/872095-babypod-a-remote-control-for-baby-buddy-for-new-pa) - A remote control for Babubi for new parents (sources: [hardware](https://github.com/skjdghsdjgsdj/babypod-hardware), [software](https://github.com/skjdghsdjgsdj/babypod-software/))
- [MatrixPortal Babubi](https://github.com/skjdghsdjgsdj/matrixportal-babybuddy)

### Mobile

- [Babubi Companion for iOS](https://apps.apple.com/app/id6788966667) ([Source](https://github.com/kguy18/babybuddyios/))
- [Babubi for Android](https://play.google.com/store/apps/details?id=eu.pkgsoftware.babybuddywidgets) ([Source](https://github.com/babybuddy/babybuddy-for-android))
- [iOS shortcuts](https://github.com/babybuddy/babybuddy/discussions/300)
- [Convert exported data from "Baby tracker - feeding, sleep and diaper" mobile app to Babubi](https://github.com/babybuddy/babybuddy/discussions/424)

### Videos

- [Babubi: Keep Records of Your Child/Baby's Growth and Activities](https://www.youtube.com/watch?v=sO6rjn2s6-k)

### Other

- [Grafana Dashboard](https://github.com/babybuddy/babybuddy/discussions/607)
- [Sandstorm app](https://github.com/babybuddy/babybuddy-sandstorm)
- Newborn parenting software series (API, buttons, LCD information screen!)
  - [part 1](https://lutzky.net/2021/10/03/software-parenting-1/)
  - [part 2](https://lutzky.net/2021/10/05/software-parenting-2/)
  - [part 3](https://lutzky.net/2021/10/10/software-parenting-3/)
- [High Level Developer Documentation (AI-Generated)](https://wiki.mutable.ai/babybuddy/babybuddy)
- [Example custom TypeScript frontend](https://github.com/jkjustjoshing/maddie-buddy) (based on [Remix](https://remix.run/))

## 🔐 Reporting Vulnerabilities

See [SECURITY.md](SECURITY.md) for information about where and how to report
potential Babubi vulnerabilities.

## ❤️ Support

### Contribution and sponsorship

Contribute or sponsor Babubi's contributors using any of the following methods:

- [Sponsor @babubi on GitHub](https://github.com/sponsors/babybuddy)
- [Sponsor @cdubz on GitHub](https://github.com/sponsors/cdubz)
- [Contribute on Open Collective](https://opencollective.com/babybuddy)

### Tools and infrastructure

The following organizations and services support Babubi contributors in various ways (software licensing, service credits, etc.).

_Some of the links below use referral codes -- all referral proceeds are treated as contributions to the Babubi project._

[![DigitalOcean Referral Badge](https://web-platforms.sfo2.cdn.digitaloceanspaces.com/WWW/Badge%203.svg)](https://www.digitalocean.com/?refcode=dd79e4cfd7b6&utm_campaign=Referral_Invite&utm_medium=Referral_Program&utm_source=badge)
[<img src="https://resources.jetbrains.com/storage/products/company/brand/logos/jb_beam.png" width="100" alt="JetBrains Logo (Main) logo.">](https://www.jetbrains.com/community/opensource/)
[![POEditor](https://poeditor.com/public/images/ui/logos/logo_dark.svg)](https://poeditor.com/)
