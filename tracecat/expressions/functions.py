import itertools
import json
import operator
import re
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from tracecat.expressions.validators import is_iterable


def _bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        return x.lower() in ("true", "1")
    # Use default bool for everything else
    return bool(x)


def _from_timestamp(x: int, unit: str) -> datetime:
    if unit == "ms":
        dt = datetime.fromtimestamp(x / 1000)
    else:
        dt = datetime.fromtimestamp(x)
    return dt


def _format_string(template: str, *values: Any) -> str:
    """Format a string with the given arguments."""
    return template.format(*values)


BUILTIN_TYPE_NAPPING = {
    "int": int,
    "float": float,
    "str": str,
    "bool": _bool,
    # TODO: Perhaps support for URLs for files?
}

# Supported Formulas / Functions
_FUNCTION_MAPPING = {
    # Comparison
    "less_than": operator.lt,
    "less_than_or_equal": operator.le,
    "greater_than": operator.gt,
    "greater_than_or_equal": operator.ge,
    "not_equal": operator.ne,
    "is_equal": operator.eq,
    "not_null": lambda x: x is not None,
    "is_null": lambda x: x is None,
    # Regex
    "regex_extract": lambda pattern, text: re.search(pattern, text).group(0),
    "regex_match": lambda pattern, text: bool(re.match(pattern, text)),
    "regex_not_match": lambda pattern, text: not bool(re.match(pattern, text)),
    # Collections
    "contains": lambda item, container: item in container,
    "does_not_contain": lambda item, container: item not in container,
    "length": len,
    "is_empty": lambda x: len(x) == 0,
    "not_empty": lambda x: len(x) > 0,
    # Math
    "add": operator.add,
    "sub": operator.sub,
    "mul": operator.mul,
    "div": operator.truediv,
    "mod": operator.mod,
    "pow": operator.pow,
    "sum": sum,
    # Transform
    "join": lambda items, sep: sep.join(items),
    "concat": lambda *items: "".join(items),
    "format": _format_string,
    # Logical
    "and": lambda a, b: a and b,
    "or": lambda a, b: a or b,
    "not": lambda a: not a,
    # Type conversion
    # Convert JSON to string
    "serialize_json": json.dumps,
    # Convert timestamp to datetime
    "from_timestamp": lambda x, unit,: _from_timestamp(x, unit),
}


P = ParamSpec("P")
R = TypeVar("R")


def mappable(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    def broadcast_map(*args: Any) -> list[Any]:
        iterables = (arg if is_iterable(arg) else itertools.repeat(arg) for arg in args)

        # Zip the iterables together and call the function for each set of arguments
        zipped_args = zip(*iterables, strict=False)
        return [func(*zipped) for zipped in zipped_args]

    wrapper.map = broadcast_map
    return wrapper


FUNCTION_MAPPING = {k: mappable(v) for k, v in _FUNCTION_MAPPING.items()}
