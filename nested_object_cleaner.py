"""Removes no longer referenced items from a nested object."""

import collections
import copy
import jsmin
import json
import os
from typing import Any, Dict, Iterable, List, Optional, OrderedDict


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


def get_summed_frequencies(freq: Dict[Any, int]):
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
    """Remove obsolete elements from nested `obj`."""

    cleaned_obj = copy.deepcopy(obj)

    matches = get_values_for_keys(obj=obj, keys=search_keys)
    freq_before = get_substr_frequency(string=json.dumps(obj), substrings=matches)

    summed_freq_before = get_summed_frequencies(freq_before)
    summed_freq_after = summed_freq_before - 1

    while summed_freq_before > summed_freq_after:
        orphaned_values = [k for k, f in freq_before.items() if f == 1]
        if orphaned_values:
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
            summed_freq_before = get_summed_frequencies(freq_before)
            summed_freq_after = get_summed_frequencies(freq_after)
            freq_before = freq_after
        else:
            # no more cleaning possible now (breaks while loop)
            summed_freq_after = summed_freq_before

    return cleaned_obj


if __name__ == "__main__":
    target_fn: str = "nested_obj_01.json"
    nested_obj = get_ordered_dict_from_file(
        fn=target_fn,
    )
    cleaned = clean_obj(
        obj=nested_obj,
        search_keys=[],
        clean_keys=[],
        ignore_paths=[],
    )
    write_dict_to_json(
        dict_=cleaned,
        fn=f"cleaned_{target_fn}",
    )
