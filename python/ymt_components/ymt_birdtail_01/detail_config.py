"""Shared guide-detail parsing for ymt_birdtail_01."""

from __future__ import annotations

import re
from typing import Optional


DETAIL_GUIDE_PATTERN = re.compile(
    r"^(?P<group>[A-Za-z][A-Za-z0-9]*)_(?P<row>\d+)_(?P<col>\d+)_loc$"
)
GROUP_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")


def parse_detail_guide_name(local_name: str) -> Optional[tuple[str, int, int]]:  # noqa: UP045
    match = DETAIL_GUIDE_PATTERN.match(local_name)
    if not match:
        return None
    return match.group("group"), int(match.group("row")), int(match.group("col"))


def is_detail_guide_name(local_name: str) -> bool:
    return parse_detail_guide_name(local_name) is not None


def parse_group_names(value: str) -> list[str]:
    names = [item.strip() for item in value.split(",") if item.strip()]
    if not names:
        raise RuntimeError("ymt_birdtail_01 groupNames cannot be empty.")
    if len(set(names)) != len(names):
        raise RuntimeError("ymt_birdtail_01 groupNames cannot contain duplicates.")
    invalid_names = [name for name in names if not GROUP_NAME_PATTERN.match(name)]
    if invalid_names:
        raise RuntimeError(
            "ymt_birdtail_01 group names must start with a letter and contain only letters or numbers: %s."
            % ", ".join(invalid_names)
        )
    return names


def parse_group_row_counts(value: str, group_names: list[str]) -> list[int]:
    raw_counts = [item.strip() for item in value.split(",") if item.strip()]
    if len(raw_counts) != len(group_names):
        raise RuntimeError(
            "ymt_birdtail_01 groupRowCounts requires exactly %s values, got %s."
            % (len(group_names), len(raw_counts))
        )
    counts = []
    for item in raw_counts:
        try:
            count = int(item)
        except ValueError as exc:
            raise RuntimeError("ymt_birdtail_01 groupRowCounts contains a non-integer value: %s." % item) from exc
        if count < 1:
            raise RuntimeError("ymt_birdtail_01 groupRowCounts values must be positive: %s." % item)
        counts.append(count)
    return counts


def parse_group_scalar_values(value: str, group_names: list[str], setting_name: str) -> list[float]:
    raw_values = [item.strip() for item in value.split(",") if item.strip()]
    if len(raw_values) != len(group_names):
        raise RuntimeError(
            "ymt_birdtail_01 %s requires exactly %s values, got %s."
            % (setting_name, len(group_names), len(raw_values))
        )
    values = []
    for item in raw_values:
        try:
            values.append(float(item))
        except ValueError as exc:
            raise RuntimeError("ymt_birdtail_01 %s contains a non-numeric value: %s." % (setting_name, item)) from exc
    return values


def parse_group_main_influence_scales(value: str, group_names: list[str]) -> list[float]:
    values = parse_group_scalar_values(value, group_names, "groupMainInfluenceScales")
    return validate_group_scale_values(values, "groupMainInfluenceScales")


def parse_group_curl_influence_scales(value: str, group_names: list[str]) -> list[float]:
    values = parse_group_scalar_values(value, group_names, "groupCurlInfluenceScales")
    return validate_group_scale_values(values, "groupCurlInfluenceScales")


def validate_group_scale_values(values: list[float], setting_name: str) -> list[float]:
    invalid_values = [item for item in values if item < 0.0 or item > 2.0]
    if invalid_values:
        raise RuntimeError(
            "ymt_birdtail_01 %s values must be between 0 and 2: %s."
            % (setting_name, ", ".join(format_float(item) for item in invalid_values))
        )
    return values


def parse_group_column_depths(value: str, group_names: list[str]) -> list[list[float]]:
    if not value.strip():
        raise RuntimeError("ymt_birdtail_01 groupColumnDepths cannot be empty.")

    named_depths, unnamed_depths = collect_group_column_depths(value)
    unknown_groups = sorted(set(named_depths).difference(group_names))
    if unknown_groups:
        raise RuntimeError("ymt_birdtail_01 groupColumnDepths has unknown groups: %s." % ", ".join(unknown_groups))
    if len(unnamed_depths) > len(group_names):
        raise RuntimeError(
            "ymt_birdtail_01 groupColumnDepths has too many unnamed rows: %s for %s groupNames."
            % (len(unnamed_depths), len(group_names))
        )

    depths_by_group = []
    for index, group_name in enumerate(group_names):
        if group_name in named_depths:
            depths = named_depths[group_name]
        elif index < len(unnamed_depths):
            depths = unnamed_depths[index]
        else:
            raise RuntimeError("ymt_birdtail_01 groupColumnDepths is missing depths for '%s'." % group_name)
        depths_by_group.append(depths)
    return depths_by_group


def collect_group_column_depths(value: str) -> tuple[dict[str, list[float]], list[list[float]]]:
    named_depths = {}
    unnamed_depths = []
    for item in split_group_column_depth_rows(value):
        name, separator, raw_depths = item.partition(":")
        if separator:
            group_name = name.strip()
            if group_name in named_depths:
                raise RuntimeError("ymt_birdtail_01 groupColumnDepths group '%s' is duplicated." % group_name)
            depths = parse_column_depth_list(raw_depths)
            named_depths[group_name] = depths
        else:
            unnamed_depths.append(parse_column_depth_list(name))
    return named_depths, unnamed_depths


def split_group_column_depth_rows(value: str) -> list[str]:
    rows = []
    for line in value.replace(";", "\n").splitlines():
        item = line.strip()
        if item:
            rows.append(item)
    return rows


def parse_column_depth_list(value: str) -> list[float]:
    values = []
    for item in [part.strip() for part in value.split(",") if part.strip()]:
        try:
            parsed = float(item)
        except ValueError as exc:
            raise RuntimeError("ymt_birdtail_01 groupColumnDepths contains a non-numeric value: %s." % item) from exc
        if not 0.0 <= parsed <= 1.0:
            raise RuntimeError("ymt_birdtail_01 groupColumnDepths values must be between 0 and 1: %s." % item)
        values.append(parsed)
    if not values:
        raise RuntimeError("ymt_birdtail_01 groupColumnDepths contains a group with no numeric values.")
    return values


def format_float(value: float) -> str:
    return ("%.4f" % value).rstrip("0").rstrip(".")


def parse_detail_curl_rot_multipliers(value: str, column_count: int) -> list[float]:
    raw_values = [item.strip() for item in value.split(",") if item.strip()]
    if len(raw_values) != column_count:
        raise RuntimeError(
            "ymt_birdtail_01 detailCurlRotMults requires exactly %s values, got %s."
            % (column_count, len(raw_values))
        )
    return parse_detail_curl_rot_multiplier_values(raw_values)


def normalize_detail_curl_rot_multipliers(value: str, column_count: int) -> list[float]:
    raw_values = [item.strip() for item in value.split(",") if item.strip()]
    values = parse_detail_curl_rot_multiplier_values(raw_values)[:column_count]
    while len(values) < column_count:
        values.append(1.0)
    return values


def parse_detail_curl_rot_multiplier_values(raw_values: list[str]) -> list[float]:
    values = []
    for item in raw_values:
        try:
            values.append(float(item))
        except ValueError as exc:
            raise RuntimeError("ymt_birdtail_01 detailCurlRotMults contains a non-numeric value: %s." % item) from exc
    return values


def format_detail_curl_rot_multipliers(values: list[float]) -> str:
    return ", ".join(format_float(value) for value in values)


def format_group_column_depths(group_names: list[str], depths_by_group: list[list[float]]) -> str:
    rows = []
    for group_name, depths in zip(group_names, depths_by_group):
        rows.append("%s: %s" % (group_name, ", ".join(format_float(depth) for depth in depths)))
    return "\n".join(rows)
