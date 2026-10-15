# Pull requests

Contributions to Babubi are welcome through GitHub [Issues](https://github.com/icon42/babubi/issues) and [Pull Requests](https://github.com/icon42/babubi/pulls).

Babubi is a fork of [Baby Buddy](https://github.com/babybuddy/babybuddy) and takes in each of its releases. A bug or feature that is not specific to Babubi is best proposed to Baby Buddy first: once it is released there, Babubi gets it with the next update.

## Caveats

### Icon font

Babubi uses [Fontello](https://fontello.com/) to build a custom icon font
for icons used throughout the application. See [`babubi/static_src/fontello`](../../babubi/static_src/fontello)
for further documentation about using the config file with Fontello and license
information for fonts used by this application.

### Pipfile

If the [Pipfile](../../Pipfile) is changed
the [requirements.txt](../../requirements.txt)
must also be updated to reflect the change. This is necessary because hosting environments
do not provide adequate support for pipenv. To update the `requirements.txt` file to be in
sync with the `Pipenv` file run:

```shell
pipenv requirements > requirements.txt
```

Add and commit the changes to the `requirements.txt` file.

### Static files

If static file assets (files in a `static_src` directory) are updated the production
static files (in the [`static` directory](../../static))
must also be updated _and committed_. This is done because it prevents the need for Node
and related tooling in deployment environments. See [`gulp updatestatic`](gulp-command-reference.md#updatestatic)
for more information on how to update the static files.

### Translations

Modifying [locale files](../../locale)
requires some extra steps. See [Translation](translation.md) for details.

## Pull request process

1. Fork this repository and commit your changes.
2. Make and commit tests for any new features or major functionality changes.
3. Run `gulp lint` and `gulp test` (see [Gulp command reference](gulp-command-reference.md))
   and ensure that all tests pass.
4. Updated static assets if necessary and commit the `/static` folder (see [`gulp updatestatic`](gulp-command-reference.md#updatestatic)).
5. Open a [new pull request](https://github.com/icon42/babubi/compare) against
   the `main` branch.

Maintainers will review new pull requests will as soon as possible, and we will
do our best to provide feedback and support potential contributors.
