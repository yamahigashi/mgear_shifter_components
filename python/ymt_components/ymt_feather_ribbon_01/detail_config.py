"""Shared detail row parsing for ymt_feather_ribbon_01."""

from __future__ import annotations

import re
from typing import Optional


DETAIL_GUIDE_PATTERNS = (
    re.compile(r"^detail_(?P<row>[A-Za-z][A-Za-z0-9]*)_(?P<col>\d+)_loc$"),
    re.compile(r"^_loc(?P<row>\d+)_(?P<col>\d+)$"),
    re.compile(r"^(?P<row>\d+)_(?P<col>\d+)_loc$"),
)
LEGACY_DETAIL_GUIDE_PATTERNS = (re.compile(r"^(?P<col>\d+)_loc$"),)
DETAIL_ROW_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")


def parse_detail_guide_name(local_name: str) -> Optional[tuple[str, int]]:  # noqa: UP045
    for pattern in DETAIL_GUIDE_PATTERNS:
        match = pattern.match(local_name)
        if match:
            return match.group("row"), int(match.group("col"))
    return None


def is_detail_guide_name(local_name: str) -> bool:
    if parse_detail_guide_name(local_name) is not None:
        return True
    return any(pattern.match(local_name) for pattern in LEGACY_DETAIL_GUIDE_PATTERNS)


def parse_row_names(value: str) -> list[str]:
    names = [item.strip() for item in value.split(",") if item.strip()]
    if not names:
        raise RuntimeError("ymt_feather_ribbon_01 rowNames cannot be empty.")
    if len(set(names)) != len(names):
        raise RuntimeError("ymt_feather_ribbon_01 rowNames cannot contain duplicates.")
    return names


def validate_detail_row_names(row_names: list[str]) -> None:
    invalid_names = [name for name in row_names if not DETAIL_ROW_NAME_PATTERN.match(name)]
    if invalid_names:
        raise RuntimeError(
            "ymt_feather_ribbon_01 detail locator row names must start with a letter and contain only letters or "
            "numbers: %s." % ", ".join(invalid_names)
        )


def parse_row_counts(value: str, row_names: list[str]) -> list[int]:
    raw_counts = [item.strip() for item in value.split(",") if item.strip()]
    if len(raw_counts) != len(row_names):
        raise RuntimeError(
            "ymt_feather_ribbon_01 rowCounts requires exactly %s values, got %s." % (len(row_names), len(raw_counts))
        )
    counts = []
    for item in raw_counts:
        try:
            count = int(item)
        except ValueError as exc:
            raise RuntimeError("ymt_feather_ribbon_01 rowCounts contains a non-integer value: %s." % item) from exc
        if count < 1:
            raise RuntimeError("ymt_feather_ribbon_01 rowCounts values must be positive: %s." % item)
        counts.append(count)
    return counts


def parse_row_u_ranges(value: str, row_names: list[str]) -> list[tuple[float, float]]:
    raw_ranges = [part.strip() for part in value.split(",") if part.strip()]
    if len(raw_ranges) != len(row_names):
        raise RuntimeError(
            "ymt_feather_ribbon_01 rowURanges requires exactly %s values, got %s." % (len(row_names), len(raw_ranges))
        )
    ranges = []
    for item in raw_ranges:
        try:
            start, end = item.split(":", 1)
            start_value = float(start)
            end_value = float(end)
        except ValueError as exc:
            raise RuntimeError("ymt_feather_ribbon_01 rowURanges contains a malformed range: %s." % item) from exc
        if not 0.0 <= start_value <= 1.0 or not 0.0 <= end_value <= 1.0:
            raise RuntimeError("ymt_feather_ribbon_01 rowURanges values must be between 0 and 1: %s." % item)
        if start_value > end_value:
            raise RuntimeError("ymt_feather_ribbon_01 rowURanges start cannot be greater than end: %s." % item)
        ranges.append((start_value, end_value))
    return ranges


def parse_lower_edge_profiles(value: str, row_names: list[str]) -> list[list[float]]:
    if not value.strip():
        raise RuntimeError("ymt_feather_ribbon_01 lowerEdgeOffsets cannot be empty.")

    named_profiles, unnamed_profiles = collect_lower_edge_profiles(value)
    validate_lower_edge_profile_rows(named_profiles, unnamed_profiles, row_names)

    profiles = []
    for index, row_name in enumerate(row_names):
        if row_name in named_profiles:
            profile = named_profiles[row_name]
        elif index < len(unnamed_profiles):
            profile = unnamed_profiles[index]
        else:
            raise RuntimeError("ymt_feather_ribbon_01 lowerEdgeOffsets is missing a profile for row '%s'." % row_name)
        profiles.append(profile)
    return profiles


def collect_lower_edge_profiles(value: str) -> tuple[dict[str, list[float]], list[list[float]]]:
    named_profiles = {}
    unnamed_profiles = []
    for item in split_lower_edge_profile_rows(value):
        name, _, raw_profile = item.partition(":")
        if raw_profile:
            row_name = name.strip()
            if row_name in named_profiles:
                raise RuntimeError("ymt_feather_ribbon_01 lowerEdgeOffsets row '%s' is duplicated." % row_name)
            profile = parse_float_list(raw_profile)
            if not profile:
                raise RuntimeError("ymt_feather_ribbon_01 lowerEdgeOffsets row '%s' has no numeric values." % name)
            named_profiles[row_name] = profile
        else:
            profile = parse_float_list(name)
            if not profile:
                raise RuntimeError("ymt_feather_ribbon_01 lowerEdgeOffsets contains a row with no numeric values.")
            unnamed_profiles.append(profile)
    return named_profiles, unnamed_profiles


def validate_lower_edge_profile_rows(
    named_profiles: dict[str, list[float]],
    unnamed_profiles: list[list[float]],
    row_names: list[str],
) -> None:
    unknown_rows = sorted(set(named_profiles).difference(row_names))
    if unknown_rows:
        raise RuntimeError("ymt_feather_ribbon_01 lowerEdgeOffsets has unknown rows: %s." % ", ".join(unknown_rows))
    if len(unnamed_profiles) > len(row_names):
        raise RuntimeError(
            "ymt_feather_ribbon_01 lowerEdgeOffsets has too many unnamed rows: %s for %s rowNames."
            % (len(unnamed_profiles), len(row_names))
        )


def split_lower_edge_profile_rows(value: str) -> list[str]:
    rows = []
    for line in value.replace(";", "\n").splitlines():
        item = line.strip()
        if item:
            rows.append(item)
    return rows


def parse_float_list(value: str) -> list[float]:
    values = []
    for item in [part.strip() for part in value.split(",") if part.strip()]:
        try:
            parsed = float(item)
        except ValueError as exc:
            raise RuntimeError(
                "ymt_feather_ribbon_01 lowerEdgeOffsets contains a non-numeric value: %s." % item
            ) from exc
        if parsed < 0.0:
            raise RuntimeError("ymt_feather_ribbon_01 lowerEdgeOffsets cannot contain negative values: %s." % item)
        values.append(parsed)
    return values


def format_lower_edge_profiles(row_names: list[str], profiles: list[list[float]]) -> str:
    rows = []
    for row_name, profile in zip(row_names, profiles):
        rows.append("%s: %s" % (row_name, ", ".join(format_float(value) for value in profile)))
    return "\n".join(rows)


def format_float(value: float) -> str:
    return ("%0.6f" % value).rstrip("0").rstrip(".")
