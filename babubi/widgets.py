import datetime

from django.forms import widgets


class DateTimeBaseInput(widgets.DateTimeBaseInput):
    def format_value(self, value):
        if isinstance(value, datetime.datetime):
            value = value.isoformat()
        return value


class DateTimeInput(DateTimeBaseInput):
    input_type = "datetime-local"

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        # Default to seconds granularity. Required for client validation in Safari.
        if "step" not in attrs:
            attrs["step"] = 1
        return attrs


class DateInput(DateTimeBaseInput):
    input_type = "date"


class TimeInput(DateTimeBaseInput):
    input_type = "time"


class DecimalInput(widgets.TextInput):
    """
    A number with decimals, typed as text: a number input only takes a point,
    and the phone keyboard of many languages offers a comma instead. Either
    one is the decimal separator (a comma only when there is no point), and
    the field is localized, so a value shows with the language's separator.
    """

    def __init__(self, attrs=None):
        super().__init__(
            {"inputmode": "decimal", "autocomplete": "off", **(attrs or {})}
        )

    def value_from_datadict(self, data, files, name):
        value = super().value_from_datadict(data, files, name)
        if isinstance(value, str) and "," in value and "." not in value:
            value = value.replace(",", ".")
        return value
