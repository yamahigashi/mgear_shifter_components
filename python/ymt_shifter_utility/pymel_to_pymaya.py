"""PyMEL to PyMaya API conversion utilities.

This module provides utilities to perform PyMEL-like operations using only Maya's Python API 2.0,
reducing dependencies on PyMEL for better performance.
"""

import math
import sys
from logging import INFO, getLogger
from typing import Union

from pymel.core import datatypes as dt

import maya.OpenMaya as om1
import maya.api.OpenMaya as om


try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm


logger = getLogger(__name__)
logger.setLevel(INFO)


# Constants
_ROT_ORDER = {
    "xyz": om.MEulerRotation.kXYZ,
    "yzx": om.MEulerRotation.kYZX,
    "zxy": om.MEulerRotation.kZXY,
    "xzy": om.MEulerRotation.kXZY,
    "yxz": om.MEulerRotation.kYXZ,
    "zyx": om.MEulerRotation.kZYX,
}

_SPACE = {
    "transform": om.MSpace.kTransform,  # Object/Local space
    "object": om.MSpace.kTransform,
    "world": om.MSpace.kWorld,
    "pre": om.MSpace.kPreTransform,  # Pre-parent space
    "post": om.MSpace.kPostTransform,  # Post-parent space
}


MatrixLike = Union[om.MTransformationMatrix, om.MMatrix, dt.TransformationMatrix]


def add_rotation(
    tm: MatrixLike,
    rot: tuple[float, float, float],
    order: str = "xyz",
    space: Union[str, om.MSpace, int] = "transform",
    unit: str = "rad",
) -> om.MTransformationMatrix:
    """Add rotation to a transformation matrix.

    Equivalent to PyMEL's TransformationMatrix.addRotation but using only Maya Python API.
    This function modifies the transformation matrix IN-PLACE.

    Args:
        tm: MTransformationMatrix, MMatrix, or datatypes.TransformationMatrix to modify
        rot: Rotation amounts (rx, ry, rz) for each axis
        order: Rotation order (case insensitive). Default is "xyz"
        space: Space for rotation - can be string, MSpace, or int. Default is "transform"
        unit: Unit for rotation values - "deg" or "rad". Default is "deg"

    Returns:
        The modified transformation matrix (same instance as input)

    Raises:
        TypeError: If tm is not a valid matrix type or space is invalid type
        ValueError: If unit or rotation order is invalid
    """

    if isinstance(tm, om.MMatrix):
        tm = om.MTransformationMatrix(tm)

    elif isinstance(tm, dt.TransformationMatrix):
        old_t = tm.getTranslation(om.MSpace.kTransform)
        old_r = tm.getRotation()
        old_s = tm.getScale(om.MSpace.kTransform)

        t = om.MVector(old_t)
        r = om.MEulerRotation(old_r)
        s = om.MVector(old_s)

        tm = om.MTransformationMatrix()
        tm.setTranslation(t, om.MSpace.kTransform)
        tm.setRotation(r)
        tm.setScale(s, om.MSpace.kTransform)

    elif not isinstance(tm, om.MTransformationMatrix):
        message = "tm must be MTransformationMatrix or MMatrix, got: "
        message += f"{type(tm).__name__}"
        raise TypeError(message)

    # Unit conversion
    if unit.lower().startswith("d"):  # degrees or deg
        rx, ry, rz = map(math.radians, rot)
    elif unit.lower().startswith("r"):  # radians or rad
        rx, ry, rz = rot
    else:
        raise ValueError('unit must be "deg" or "rad"')

    # Create MEulerRotation
    try:
        euler_order = _ROT_ORDER[order.lower()]
    except KeyError as err:
        raise ValueError(f"rotation order must be one of: {', '.join(_ROT_ORDER.keys())}") from err
    delta_euler = om.MEulerRotation(rx, ry, rz, euler_order)

    # Determine application space
    try:
        if isinstance(space, (om.MSpace, int)):
            mspace = space
        elif isinstance(space, str):
            mspace = _SPACE[space.lower()]
        else:
            raise TypeError("space must be MSpace, int, or str")
    except KeyError as err:
        raise ValueError(f"space must be one of: {', '.join(_SPACE.keys())}") from err

    # Apply rotation
    # MTransformationMatrix.rotateBy adds the given rotation incrementally,
    # which is equivalent to PyMEL's addRotation. The return value (bool) is ignored.
    tm.rotateBy(delta_euler, mspace)
    return tm
