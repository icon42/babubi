# Translation

Babubi's translations come from Baby Buddy's translators. Babubi edits the `.po` files under `locale/` directly, with any PO editor such as [Poedit](https://poedit.net/), and takes changes through [pull requests](pull-requests.md). Baby Buddy collects its translations on [POEditor](https://poeditor.com/); a fix that also applies to Baby Buddy is best made there, so both projects get it.

## Adding or updating a language

A translation process will look something like this:

1. Set up a development environment (see [Development environment](development-environment.md)).

2. Run `gulp makemessages -l xx` where `xx` is a specific locale code in the
   [ISO 639-1 format](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g.,
   "il" for Italian or "es" for Spanish). This creates a new translation file at
   `locale/xx/LC_MESSAGES/django.po`, or updates one if it exists.

3. Open the created/updated `django.po` file and update the header template
   with license and contact info.

4. Start translating! Each translatable string will have a `msgid` value with
   the string in English and a corresponding (empty) `msgstr` value where a
   translated string can be filled in.

5. Once all strings have been translated, run `gulp compilemessages -l xx` to
   compile an optimized translation file (`locale/xx/LC_MESSAGES/django.mo`).

6. To expose the new translation as a user setting, add the locale code to the
   `LANGUAGES` array in the base settings file (`babubi/settings/base.py`).

7. Check if Plotly offers a translation (in `node_modules/plotly.js/dist/`) for
   the language. If it does:
   1. Add the Plotly translation file path to [`gulpfile.config.js`](../../gulpfile.config.js)
      in `scriptsConfig.graph`.

   2. Build, collect, and commit the `/static` folder (see [`gulp updatestatic`](gulp-command-reference.md#updatestatic)).

8. Run the development server, log in, and update the user language to test the
   newly translated strings.

Once the translation is complete, commit the new files and changes to a fork
and [create a pull request](pull-requests.md) for review.

For more information on the Django translation process, see Django's
documentation section: [Translation](https://docs.djangoproject.com/en/5.0/topics/i18n/translation/).
