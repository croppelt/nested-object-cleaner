"""Removes no longer referenced items from a nested object."""

import argparse
import collections
import copy
import jsmin
import json
import os
from typing import Any, Dict, Iterable, List, Optional, OrderedDict


# Default settings used if not set otherwise via the Command Line Interface
DEFAULT_SEARCH_KEYS: Iterable[str] = ("name", "fromDict", "sourceName")
DEFAULT_TARGET_KEYS: Iterable[str] = ("name",)
DEFAULT_IGNORED_PATHS: Iterable[str] = ()


def get_ordered_dict_from_file(fn: str) -> OrderedDict:
    """Read file content (e.g. a nested object) into an OrderedDict."""
    with open(os.path.abspath(fn), "r") as read_file:
        as_str = jsmin.jsmin(read_file.read())
        return collections.OrderedDict(json.loads(as_str))


def write_dict_to_json(dict_: dict, fn: str, sort_keys: bool = False) -> None:
    """Write `dict` as JSON to specified file."""
    with open(os.path.abspath(fn), "w") as write_file:
        json.dump(dict_, write_file, sort_keys=sort_keys, indent=2)


def get_values_for_keys(
    obj: Any, keys: Iterable[Any], values: Optional[set] = None
) -> set:
    """Get all values for `keys` found in nested `obj`."""
    if not values:
        values = set()

    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys:
                values.add(v)
            else:
                values = get_values_for_keys(obj=v, keys=keys, values=values)
    elif isinstance(obj, list):
        for element in obj:
            values = get_values_for_keys(obj=element, keys=keys, values=values)

    return values


def get_substr_frequency(string: str, substrings: Iterable[str]) -> Dict[str, int]:
    """Get dictionary with frequencies (vals) of substrings (keys) in given string."""
    return {s: string.count(s) for s in substrings}


def summed_frequencies(freq: Dict[Any, int]):
    """Get total sum of frequencies in given frequency dict."""
    return sum(freq.values())


def _prune_dict(dict_, on_keys, for_values, ignore_paths, path):
    """Type-specific helper for `prune_obj`."""
    pruned = {}
    for k, v in dict_.items():
        if k in on_keys and v in for_values:
            # current `obj` matches pruning criteria: do *not* return it
            return None
        elif v:
            # recursively prune current key's value
            path.append(k)
            pruned_v = prune_obj(
                obj=v,
                on_keys=on_keys,
                for_values=for_values,
                ignore_paths=ignore_paths,
                path=path,
            )
            if pruned_v:
                pruned[k] = pruned_v
            path.pop()
        else:
            # catch and return empty value; it may be meaningful
            pruned[k] = v
    return pruned


def _prune_list(list_, on_keys, for_values, ignore_paths, path):
    """Type-specific helper for `prune_obj`."""
    pruned = []
    for element in list_:
        if element:
            # recursively prune current element
            pruned_e = prune_obj(
                obj=element,
                on_keys=on_keys,
                for_values=for_values,
                ignore_paths=ignore_paths,
                path=path
            )
            if pruned_e:
                pruned.append(pruned_e)
        else:
            # catch and return empty element; it may be meaningful
            pruned.append(element)
    return pruned


def prune_obj(
    obj: Any,
    on_keys: Iterable[Any],
    for_values: Iterable[Any],
    ignore_paths: Optional[Iterable[str]] = None,
    path: Optional[List[Any]] = None,
) -> Any:
    """Remove elements from nested `obj` where given keys match specified values."""
    if not path:
        path = []
    if ignore_paths and path and ".".join(path) in ignore_paths:
        return obj  # current path is 'blacklisted': won't inspect it further/deeper
    if isinstance(obj, dict):
        pruned = _prune_dict(
            dict_=obj,
            on_keys=on_keys,
            for_values=for_values,
            ignore_paths=ignore_paths,
            path=path,
        )
    elif isinstance(obj, list):
        pruned = _prune_list(
            list_=obj,
            on_keys=on_keys,
            for_values=for_values,
            ignore_paths=ignore_paths,
            path=path
        )
    else:
        return obj

    return pruned


def clean_obj(
    obj: Any,
    search_keys: Iterable[Any],
    clean_keys: Iterable[Any],
    ignore_paths: Optional[Iterable[str]] = None,
) -> Any:
    """Remove obsolete items from nested `obj`.

    To remove obsolete items from a nested object such as a nested dictionary or
    list, you can specify all the keys that identify an item in your nested object
    via `search_keys`, and all the keys in which these values may be used in your
    object via `clean_keys`. This would remove all items anywhere in your nested
    where any of the item's keys is in `clean_keys` *and* matches any of the values
    found for any key in `search_keys` that exists *only once* in the object. In
    other words, identifying values that are not referenced anywhere else in your
    nested object are considered obsolete and thus are removed.

    Parameters
    ----------
    obj
        The nested target object.
    search_keys
        Keys anywhere in `obj` whose values are collected and counted. Values that
        only occur once indicate an obsolete item when they are used as a value for
        any key in `clean_keys`.
    clean_keys
        Keys anywhere in `obj` whose parent item (i.e., the item that contains this
        key) is removed from `obj` when its value occurs only once for any of the
        keys in `search_keys`.
    ignore_paths
        Paths (including their substructures) through `obj` that are excluded from
        cleaning: no items in and below these paths will be removed from `obj`. A
        path here must be described by the sequence of its keys, separated by a dot.
        For instance, "config.foo.bar" would prevent `config[foo][bar][<...>]` from
        being cleaned.

    Returns
    -------
    Cleaned deep copy of `obj`.

    """
    cleaned_obj = copy.deepcopy(obj)

    matches = get_values_for_keys(obj=obj, keys=search_keys)

    while True:
        freq_before = get_substr_frequency(
            string=json.dumps(cleaned_obj),
            substrings=matches,
        )
        if orphaned_values := [k for k, f in freq_before.items() if f == 1]:
            cleaned_obj = prune_obj(
                obj=cleaned_obj,
                on_keys=clean_keys,
                for_values=orphaned_values,
                ignore_paths=ignore_paths,
            )
        freq_after = get_substr_frequency(
            string=json.dumps(cleaned_obj),
            substrings=matches,
        )
        if summed_frequencies(freq_after) == summed_frequencies(freq_before):
            break

    return cleaned_obj


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Remove no longer referenced items from a nested object",
        fromfile_prefix_chars='@',
    )
    parser.add_argument(
        "file",
        action="store",
        type=str,
        help="path to target file containing the nested object to be cleaned",
    )
    parser.add_argument(
        "-s",
        "--search-in",
        action="store",
        type=str,
        nargs="*",
        default=DEFAULT_SEARCH_KEYS,
        help="keys whose values are collected and counted",
    )
    parser.add_argument(
        "-t",
        "--target-keys",
        action="store",
        type=str,
        nargs="*",
        default=DEFAULT_TARGET_KEYS,
        help="keys that trigger removal of their parent when orphaned",
    )
    parser.add_argument(
        "-i",
        "--ignore-paths",
        action="store",
        type=str,
        nargs="*",
        default=DEFAULT_IGNORED_PATHS,
        help="paths in which items will never be removed",
    )
    args = parser.parse_args()

    nested_obj = get_ordered_dict_from_file(
        fn=args.file,
    )
    cleaned = clean_obj(
        obj=nested_obj,
        search_keys=args.search_in,
        clean_keys=args.target_keys,
        ignore_paths=args.ignore_paths,
    )
    write_dict_to_json(
        dict_=cleaned,
        fn=f"{os.path.dirname(args.file)}/cleaned_{os.path.basename(args.file)}",
    )
