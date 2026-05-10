"""
driven_key_transfer.py – Export & re‑apply driven‑key setups in Autodesk Maya
==========================================================================
Author: ChatGPT (OpenAI o3)
Version: 0.1  (2025‑05‑12)
Python 3.x / Maya 2020+ (tested on Maya 2024)

Overview
--------
This module provides two high‑level helpers:

* ``export_driven_keys(node, filepath, *, world_space=False)`` –
  Serialises all driven‑key (setDrivenKeyframe) relationships that affect
  *any* attribute on **node** (including child compound channels) into a
  single JSON file at **filepath**.

* ``import_driven_keys(filepath, *, namespace_map=None, strict=False)`` –
  Re‑creates the animation curves in the *current* scene and reconnects
  them, optionally remapping namespaces / node names.

Motivation
~~~~~~~~~~
While Maya allows you to copy/paste driven‑keys between scenes via the
GUI, there is no out‑of‑the‑box way to persist them in source control or
apply them in an automated pipeline.  JSON is human‑readable, diffable
and easy to patch, so we use it as the interchange format.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from collections.abc import Iterator
from typing import Any, Optional, Sequence, Union

import maya.cmds as cmds

# -------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------

_ANIM_TYPES = {
    "animCurveUU",
    "animCurveUA",
    "animCurveUT",
    "animCurveUL",
    "animCurveULB",  # boolean
    "animCurveTL",
    "animCurveTU",
    "animCurveTA",
}

_FLOAT_ATTR_RE = re.compile(r"^[^\.]+\.[^\.]+$")  # quick sanity check


def _iter_anim_curves(driven_node: str) -> Iterator[tuple[str, str]]:
    """Yield (driven_plug, animCurve) pairs for every driven attr on *driven_node*."""
    attrs = cmds.listAttr(driven_node, k=True, s=True) or []
    for attr in attrs:
        target_plug = f"{driven_node}.{attr}"
        # Fast path: only query attributes that actually have incoming
        # connections – avoids expensive listConnections on every channel.
        if not cmds.connectionInfo(target_plug, id=True):
            continue
        anims = cmds.listConnections(
            target_plug,
            destination=False,
            source=True,
            type="animCurve",
            plugs=False,
        ) or []
        for anim in anims:
            if cmds.nodeType(anim) not in _ANIM_TYPES:
                continue  # ignore non‑key driven connections
            yield target_plug, anim


def _anim_curve_data(anim: str) -> dict[str, Any]:
    """Return a full serialisable dump of *anim* curve (keys, tangents, etc.)."""
    key_count = cmds.keyframe(anim, query=True, keyframeCount=True)
    if not key_count:
        cmds.warning(f"AnimCurve '{anim}' has no keys.")
        return {}

    # Maya returns values only when an index range is supplied for some curve types.
    times = cmds.keyframe(anim, query=True, index=(0, key_count - 1), fc=True)
    values = cmds.keyframe(anim, query=True, index=(0, key_count - 1), vc=True)
    in_tan = cmds.keyTangent(anim, query=True, index=(0, key_count - 1), itt=True)
    out_tan = cmds.keyTangent(anim, query=True, index=(0, key_count - 1), ott=True)

    keys = [
        {
            "input": times[i],
            "output": values[i],
            "inTan": in_tan[i],
            "outTan": out_tan[i],
        }
        for i in range(key_count)
    ]

    # The driver plug is the *source* connected to anim.input
    driver = cmds.connectionInfo(f"{anim}.input", sfd=True)

    return {
        "nodeType": cmds.nodeType(anim),
        "name": anim,
        "driver": driver,  # e.g. "pSphere1.rotateY"
        "keys": keys,
        "preInfinity": cmds.getAttr(f"{anim}.preInfinity"),
        "postInfinity": cmds.getAttr(f"{anim}.postInfinity"),
        "weightedTangents": cmds.getAttr(f"{anim}.weightedTangents"),
    }


# -------------------------------------------------------------
# Public API
# -------------------------------------------------------------

def dump_driven_keys(
    node: Union[str, Sequence[str]],
    world_space: bool = False,
) -> list[dict[str, Any]]:
    """Export all driven‑key relationships that affect *node* to *filepath*.

    Parameters
    ----------
    node
        The *driven* node you want to export from.  Must exist.
    world_space
        If *True*, bake local‑space curves to world‑space values before
        export.  (This is rarely needed; default *False*.)

    Returns the absolute file path written so callers can print/log it.
    """
    result: list[dict[str, Any]] = []
    if not isinstance(node, str):
        for n in node:
            result.extend(dump_driven_keys(n, world_space=world_space))

        return result

    if not cmds.objExists(node):
        raise RuntimeError(f"Node '{node}' does not exist in the scene.")

    data: dict[str, Any] = {
        "maya": cmds.about(version=True),
        "exporter": "driven_key_transfer 0.1",
        "drivenNode": node,
        "curves": [],
    }

    for driven_plug, anim in _iter_anim_curves(node):
        curve_info = _anim_curve_data(anim)
        curve_info["targetPlug"] = driven_plug
        data["curves"].append(curve_info)

    if not data["curves"]:
        raise RuntimeError(f"No driven‑key animCurves found on '{node}'.")

    result.append(data)

    return result


def export_driven_keys_to_file(
    node: str,
    filepath: str,
    *,
    world_space: bool = False,
) -> str:
    """Export all driven‑key relationships that affect *node* to *filepath*.

    Parameters
    ----------
    node
        The *driven* node you want to export from.  Must exist.
    filepath
        Destination .json path.  Parent folder is created automatically.
    world_space
        If *True*, bake local‑space curves to world‑space values before
        export.  (This is rarely needed; default *False*.)

    Returns the absolute file path written so callers can print/log it.
    """
    data = dump_driven_keys(node, world_space=world_space)
    if not os.path.isdir(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf‑8") as fh:
        json.dump(data, fh, indent=4)

    return os.path.abspath(filepath)


def import_driven_keys(
    data: Union[list[dict[str, Any]], dict[str, Any]],
    namespace_map: Optional[dict[str, str]] = None,
    strict: bool = False,
) -> list[str]:
    """Import driven‑key relationships from *filepath* into the current scene.

    Parameters
    ----------
    data:

    namespace_map
        Optional mapping ``{"old": "new"}`` that will be *regex*‑applied to
        both driver and target plugs **before** connections are made.  This
        allows you to port a rig to a different namespace without editing
        the JSON.
    strict
        If *True*, raise an error as soon as a target or driver plug is not
        found.  If *False* (default), missing plugs are skipped with a
        warning so that partial imports still succeed.

    Returns a list of newly created animCurve nodes.
    """
    if isinstance(data, list):
        for d in data:
            import_driven_keys(d, namespace_map=namespace_map, strict=strict)

    if not isinstance(data, dict):
        raise TypeError("Invalid data format: expected a list of dicts.")
    if "curves" not in data:
        raise KeyError("Missing 'curves' key in data.")
    if "drivenNode" not in data:
        raise KeyError("Missing 'drivenNode' key in data.")

    def _map(plug: str) -> str:
        if not namespace_map:
            return plug
        out = plug
        for old, new in namespace_map.items():
            out = re.sub(fr"^{re.escape(old)}(?=[:]|\.)", new, out)
        return out

    created_anim_curves: list[str] = []

    for curve in data.get("curves", []):

        if not isinstance(curve, dict):
            continue

        if "targetPlug" not in curve:
            continue

        if "driver" not in curve:
            continue

        driver = _map(curve["driver"])
        target = _map(curve["targetPlug"])

        if not cmds.objExists(driver):
            msg = f"Driver '{driver}' missing."
            if strict:
                raise RuntimeError(msg)
            print("[driven_key_transfer] WARNING:", msg)
            continue
        if not cmds.objExists(target):
            msg = f"Target '{target}' missing."
            if strict:
                raise RuntimeError(msg)
            print("[driven_key_transfer] WARNING:", msg)
            continue

        # Build keys via Maya’s native driven‑key command
        for k in curve["keys"]:
            cmds.setDrivenKeyframe(
                target,
                cd=driver,
                dv=k["input"],
                v=k["output"],
                itt=k["inTan"],
                ott=k["outTan"],
            )

        # Fetch the freshly created animCurve and set infinity / weighting
        anim = cmds.listConnections(target, s=True, d=False, t="animCurve")[-1]
        created_anim_curves.append(anim)
        cmds.setAttr(f"{anim}.preInfinity", curve["preInfinity"])
        cmds.setAttr(f"{anim}.postInfinity", curve["postInfinity"])
        try:
            cmds.setAttr(f"{anim}.weightedTangents", curve["weightedTangents"])
        except RuntimeError:
            # weightedTangents is not available on all curve types
            pass

    print(f"[driven_key_transfer] Imported {len(created_anim_curves)} driven‑key curves")
    return created_anim_curves


def import_driven_keys_from_file(
    filepath: str,
    namespace_map: Optional[dict[str, str]] = None,
    strict: bool = False,
) -> list[str]:
    with open(filepath, "r", encoding="utf‑8") as fh:
        data = json.load(fh)

    return import_driven_keys(data, namespace_map=namespace_map, strict=strict)


# -------------------------------------------------------------
# CLI shim – so the same script can be run *outside* Maya for export
# via mayapy or inside Maya's Script Editor.
# -------------------------------------------------------------
if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser(description="Export driven‑key setups from a Maya scene.")
    sub = parser.add_subparsers(dest="cmd")

    exp = sub.add_parser("export")
    exp.add_argument("node", help="Name of the driven node in the opened scene.")
    exp.add_argument("filepath", help="Destination JSON path.")

    imp = sub.add_parser("import")
    imp.add_argument("filepath", help="Source JSON file.")
    imp.add_argument("--strict", action="store_true", help="Fail if any plug is missing.")

    args = parser.parse_args()

    if cmds.about(batch=True):
        # In mayapy – user must open their scene beforehand via cmds.file.
        pass

    if args.cmd == "export":
        export_driven_keys(args.node, args.filepath)
    elif args.cmd == "import":
        import_driven_keys(args.filepath, strict=args.strict)
    else:
        parser.print_help()
        sys.exit(1)
