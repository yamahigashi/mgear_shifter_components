"""Shared detail row parsing for ymt_feather_ribbon_01."""

from __future__ import annotations

import re
from typing import Optional


# Detail guide locator names encode their row and grid position.
#
#     primary_0_2_loc
#     |       | |
#     |       | +-- col: feather part index, from feather root to feather tip
#     |       +---- section: feather index along the wing span
#     +------------ row: rowNames entry
#
# The same indices map to the feather layout like this:
#
#     wing root -------------------------------------------- wing tip
#        section 0        section 1        section 2
#     +--------------+--------------+--------------+
# row primary        primary_0_0    primary_1_0    primary_2_0
#                     primary_0_1    primary_1_1    primary_2_1
#                      primary_0_2    primary_1_2    primary_2_2
#
# row secondary      secondary_0_0  secondary_1_0  secondary_2_0
#                     secondary_0_1  secondary_1_1  secondary_2_1
#
# Each row is a feather row such as primary/secondary/tertial. Section picks
# which feather along the wing span, and col picks a part on that feather from
# its root toward its tip. The number of col parts comes from detailColumnDepths.
# detailColumnDepths places cols on the anchor -> anchorEnd depth axis:
# 0.0 is the anchor line, and 1.0 is the anchorEnd reference line.
#
# Feather view:
#
#     root / arm side                                      tip / hand side
#
#     primary row
#          \ primary_0_0     \ primary_1_0     \ primary_2_0
#           \ primary_0_1     \ primary_1_1     \ primary_2_1
#            \ primary_0_2     \ primary_1_2     \ primary_2_2
#
#     secondary row
#             \ secondary_0_0  \ secondary_1_0  \ secondary_2_0
#              \ secondary_0_1  \ secondary_1_1  \ secondary_2_1
#
#     tertial row
#                \ tertial_0_0  \ tertial_1_0  \ tertial_2_0
#
# Rebuild Detail Locators writes this name, setFromHierarchy serializes it,
# and the rig build parses it back into the DetailSpec row/section/col.
DETAIL_GUIDE_PATTERNS = (
    re.compile(r"^(?P<row>[A-Za-z][A-Za-z0-9]*)_(?P<section>\d+)_(?P<col>\d+)_loc$"),
)
DETAIL_ROW_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")


def parse_detail_guide_name(local_name: str) -> Optional[tuple[str, int, int]]:  # noqa: UP045
    for pattern in DETAIL_GUIDE_PATTERNS:
        match = pattern.match(local_name)
        if match:
            return match.group("row"), int(match.group("section")), int(match.group("col"))
    return None


def is_detail_guide_name(local_name: str) -> bool:
    return parse_detail_guide_name(local_name) is not None


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


def parse_detail_column_depths_by_row(value: str, row_names: list[str]) -> list[list[float]]:
    if not value.strip():
        raise RuntimeError("ymt_feather_ribbon_01 detailColumnDepths cannot be empty.")

    named_depths_by_row, unnamed_depth_rows = collect_detail_column_depths_by_row(value)
    validate_detail_column_depth_rows(named_depths_by_row, unnamed_depth_rows, row_names)

    depths_by_row = []
    for index, row_name in enumerate(row_names):
        if row_name in named_depths_by_row:
            depths = named_depths_by_row[row_name]
        elif index < len(unnamed_depth_rows):
            depths = unnamed_depth_rows[index]
        else:
            raise RuntimeError("ymt_feather_ribbon_01 detailColumnDepths is missing a depth row for '%s'." % row_name)
        depths_by_row.append(depths)
    return depths_by_row


def collect_detail_column_depths_by_row(value: str) -> tuple[dict[str, list[float]], list[list[float]]]:
    named_depths_by_row = {}
    unnamed_depth_rows = []
    for item in split_detail_column_depth_rows(value):
        name, _, raw_depths = item.partition(":")
        if raw_depths:
            row_name = name.strip()
            if row_name in named_depths_by_row:
                raise RuntimeError("ymt_feather_ribbon_01 detailColumnDepths row '%s' is duplicated." % row_name)
            depths = parse_detail_column_depth_list(raw_depths)
            if not depths:
                raise RuntimeError("ymt_feather_ribbon_01 detailColumnDepths row '%s' has no numeric values." % name)
            named_depths_by_row[row_name] = depths
        else:
            depths = parse_detail_column_depth_list(name)
            if not depths:
                raise RuntimeError("ymt_feather_ribbon_01 detailColumnDepths contains a row with no numeric values.")
            unnamed_depth_rows.append(depths)
    return named_depths_by_row, unnamed_depth_rows


def validate_detail_column_depth_rows(
    named_depths_by_row: dict[str, list[float]],
    unnamed_depth_rows: list[list[float]],
    row_names: list[str],
) -> None:
    unknown_rows = sorted(set(named_depths_by_row).difference(row_names))
    if unknown_rows:
        raise RuntimeError("ymt_feather_ribbon_01 detailColumnDepths has unknown rows: %s." % ", ".join(unknown_rows))
    if len(unnamed_depth_rows) > len(row_names):
        raise RuntimeError(
            "ymt_feather_ribbon_01 detailColumnDepths has too many unnamed rows: %s for %s rowNames."
            % (len(unnamed_depth_rows), len(row_names))
        )


def split_detail_column_depth_rows(value: str) -> list[str]:
    rows = []
    for line in value.replace(";", "\n").splitlines():
        item = line.strip()
        if item:
            rows.append(item)
    return rows


def parse_detail_column_depth_list(value: str) -> list[float]:
    values = []
    for item in [part.strip() for part in value.split(",") if part.strip()]:
        try:
            parsed = float(item)
        except ValueError as exc:
            raise RuntimeError(
                "ymt_feather_ribbon_01 detailColumnDepths contains a non-numeric value: %s." % item
            ) from exc
        if not 0.0 <= parsed <= 1.0:
            raise RuntimeError("ymt_feather_ribbon_01 detailColumnDepths values must be between 0 and 1: %s." % item)
        values.append(parsed)
    return values


def parse_detail_curl_rot_multipliers(value: str, column_count: int) -> list[float]:
    raw_values = split_detail_curl_rot_multipliers(value)
    if len(raw_values) != column_count:
        raise RuntimeError(
            "ymt_feather_ribbon_01 detailCurlRotMults requires exactly %s values, got %s."
            % (column_count, len(raw_values))
        )
    return parse_detail_curl_rot_multiplier_values(raw_values)


def normalize_detail_curl_rot_multipliers(value: str, column_count: int) -> list[float]:
    raw_values = split_detail_curl_rot_multipliers(value)
    values = parse_detail_curl_rot_multiplier_values(raw_values)[:column_count]
    while len(values) < column_count:
        values.append(1.0)
    return values


def split_detail_curl_rot_multipliers(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_detail_curl_rot_multiplier_values(raw_values: list[str]) -> list[float]:
    values = []
    for item in raw_values:
        try:
            values.append(float(item))
        except ValueError as exc:
            raise RuntimeError("ymt_feather_ribbon_01 detailCurlRotMults contains a non-numeric value: %s." % item) from exc
    return values


def format_detail_column_depths_by_row(row_names: list[str], depths_by_row: list[list[float]]) -> str:
    rows = []
    for row_name, depths in zip(row_names, depths_by_row):
        rows.append("%s: %s" % (row_name, ", ".join(format_float(value) for value in depths)))
    return "\n".join(rows)


def format_detail_curl_rot_multipliers(values: list[float]) -> str:
    return ", ".join(format_float(value) for value in values)


def format_float(value: float) -> str:
    return ("%0.6f" % value).rstrip("0").rstrip(".")
