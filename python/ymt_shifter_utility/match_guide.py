# -*- coding: utf-8 -*-  # noqa
"""Maya Rigging Utilities

Provides functionality for matching, connecting, and constraining nodes in Maya.
"""
import contextlib
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from logging import DEBUG, INFO, WARN, StreamHandler, getLogger  # NOQA

import anyconfig
import six

import maya.cmds as cmds
from maya.api import OpenMaya as OpenMaya2


# for python2 type annotations
if sys.version_info >= (3, 0):
    # For type annotation
    from typing import (  # NOQA: F401 pylint: disable=unused-import
        Any,
        Callable,
        Optional,
        Text,
        Union,
    )

try:
    import gml_maya.util as util  # type: ignore
except ImportError:
    class _DummyUtil:
        @staticmethod
        def displayable_path(x):
            return x
    util = _DummyUtil()

##############################################################################
# Logging setup
##############################################################################
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)     # ハンドラーは DEBUG
logger.setLevel(INFO)       # ロガーのレベルは INFO
logger.addHandler(handler)
logger.propagate = False


##############################################################################
# Classes
##############################################################################
class MGOption:
    """Configuration options for node matching and connection operations.

    Attributes:
        alias_definition_path (str or None): Path to alias definition file
        dst_alias (bool): Whether to apply aliases to destination nodes
        src_alias (bool): Whether to apply aliases to source nodes
        dst_multiple (bool): Whether to allow multiple destination nodes
        alias_definition (dict or None): Loaded alias definitions
    """

    def __init__(self, alias_definition=None, dst_alias=False, src_alias=False, dst_multiple=False):
        # type: (Optional[str], bool, bool, bool) -> None
        """Initialize MGOption."""
        self.alias_definition_path = alias_definition

        # alias_definition が有効ファイルでなければ alias をオフ
        if alias_definition and os.path.exists(alias_definition):
            self.dst_alias = dst_alias
            self.src_alias = src_alias
        else:
            self.dst_alias = False
            self.src_alias = False

        self.dst_multiple = dst_multiple
        self.alias_definition = None

        if self.alias_definition_path is not None and os.path.exists(self.alias_definition_path):
            self._load_alias_definition()

    def _load_alias_definition(self):
        # type: () -> None
        """Load alias definitions from XML file."""
        self.alias_definition = {}

        if self.alias_definition_path is None:
            logger.warning("alias_definition is None")
            return

        if not os.path.exists(self.alias_definition_path):
            logger.warning(f"alias_definition file not found: {self.alias_definition_path}")
            return

        logger.warning(f"alias_definition: {self.alias_definition_path}")
        try:
            root = ET.parse(self.alias_definition_path).getroot()
            # 単純に root[0] 以下を解析する前提
            if not list(root):
                logger.warning(f"No child elements in alias_definition XML: {self.alias_definition_path}")
                return

            first_child = root[0]
            for entry in first_child:
                attrs = entry.attrib
                self.alias_definition[attrs.get("key")] = attrs.get("value")
        except (ET.ParseError, IndexError) as e:
            logger.error(f"Failed to parse alias definition: {e}")


##############################################################################
# Node Utility Functions
##############################################################################


def get_node(node_name):
    # type: (Text) -> Optional[OpenMaya2.MDagPath]
    """Get Maya node(s) by name.

    Args:
        node_name: The name of the node to get

    Returns:
        MDagPath object(s) for the node(s) or None if not found
    """
    candidates = cmds.ls(node_name, recursive=True)
    if not candidates:
        return None

    results = []
    for candidate in candidates:
        try:
            selection = OpenMaya2.MGlobal.getSelectionListByName(candidate)
            results.append(selection)
        except RuntimeError:
            pass

    dag_paths = []
    for result in results:
        try:
            dag_paths.append(result.getDagPath(0))
        except Exception:
            logger.error(f"Cannot getDagPath for {node_name}, using MObject instead")
            dag_paths.append(result.getDependNode(0))

    if not dag_paths:
        return None

    return dag_paths[0]


def get_nodes(node_name):
    # type: (Text) -> Optional[list[OpenMaya2.MDagPath]]
    """Get Maya node(s) by name.

    Args:
        node_name: The name of the node to get

    Returns:
        MDagPath object(s) for the node(s) or None if not found
    """
    candidates = cmds.ls(node_name, recursive=True)
    if not candidates:
        return None

    results = []
    for candidate in candidates:
        try:
            selection = OpenMaya2.MGlobal.getSelectionListByName(candidate)
            results.append(selection)
        except RuntimeError:
            pass

    dag_paths = []
    for result in results:
        try:
            dag_paths.append(result.getDagPath(0))
        except Exception:
            logger.error(f"Cannot getDagPath for {node_name}, using MObject instead")
            dag_paths.append(result.getDependNode(0))

    if not dag_paths:
        return None

    return dag_paths


def apply_alias(name, definition):
    # type: (Text, dict[Text, Text]) -> Text
    """Apply alias to name if defined in the definition.

    Args:
        name: Original name
        definition: Alias definition dictionary

    Returns:
        Aliased name or original name if no alias defined
    """
    if definition is not None:
        return definition.get(name) or name
    return name


##############################################################################
# Transform Functions
##############################################################################


def get_rotation(dag_path, space=OpenMaya2.MSpace.kWorld):
    # type: (OpenMaya2.MDagPath, Union[int, OpenMaya2.MSpace]) -> OpenMaya2.MQuaternion
    """Get rotation of a node as quaternion.

    Args:
        dag_path: The MDagPath of the node
        space: The coordinate space to get rotation in

    Returns:
        Quaternion rotation of the node
    """
    try:
        transform = OpenMaya2.MFnTransform(dag_path)
        rotation = transform.rotation(space, True)  # as quat
    except RuntimeError as e:
        logger.error(f"Failed to get rotation for {dag_path.fullPathName()}: {e}")
        raise

    # If space != kWorld, we optionally add the jointOrient
    if space != OpenMaya2.MSpace.kWorld:
        try:
            jo = cmds.getAttr(f"{dag_path.fullPathName()}.jointOrient")[0]
            euler = OpenMaya2.MEulerRotation(math.radians(jo[0]),
                                             math.radians(jo[1]),
                                             math.radians(jo[2]))
            rotation = rotation * euler.asQuaternion()
        except (RuntimeError, ValueError):
            pass

    return rotation


def set_rotation(dag_path, quat, space=OpenMaya2.MSpace.kWorld):
    # type: (OpenMaya2.MDagPath, OpenMaya2.MQuaternion, Union[int, OpenMaya2.MSpace]) -> None
    """Set rotation of a node (Quaternion).

    Args:
        dag_path: The MDagPath of the node
        quat: Quaternion rotation to set
        space: The coordinate space to set rotation in
    """
    transform = OpenMaya2.MFnTransform(dag_path)
    path_name = dag_path.fullPathName()

    # Place node to world space to avoid parent negative scale
    parent = cmds.listRelatives(path_name, parent=True)
    if parent:
        cmds.parent(path_name, world=True)

    # Always set in world space to avoid double transformations
    transform.setRotation(quat, OpenMaya2.MSpace.kWorld)

    # Restore parenting
    if parent:
        cmds.parent(path_name, parent[0])


def get_translation(dag_path, space=OpenMaya2.MSpace.kWorld):
    # type: (OpenMaya2.MDagPath, Union[int, OpenMaya2.MSpace]) -> OpenMaya2.MVector
    """Get translation of a node.

    Args:
        dag_path: The MDagPath of the node
        space: The coordinate space to get translation in

    Returns:
        MVector translation of the node
    """
    transform = OpenMaya2.MFnTransform(dag_path)
    return transform.translation(space)


def set_translation(dag_path, value, space=OpenMaya2.MSpace.kWorld):
    # type: (OpenMaya2.MDagPath, OpenMaya2.MVector, Union[int, OpenMaya2.MSpace]) -> None
    """Set translation of a node.

    Args:
        dag_path: The MDagPath of the node
        value: MVector translation to set
        space: The coordinate space to set translation in
    """
    transform = OpenMaya2.MFnTransform(dag_path)
    transform.setTranslation(value, space)


##############################################################################
# Constraint & Connection Functions
##############################################################################


def connect_attr(source, destination):
    # type: (Text, Text) -> None
    """Connect one attribute to another.

    Args:
        source: Source attribute path (node.attribute)
        destination: Destination attribute path (node.attribute)
    """
    s_obj = cmds.ls(source.split(".")[0], r=True)
    d_obj = cmds.ls(destination.split(".")[0], r=True)
    if not s_obj or not d_obj:
        logger.error(f"connectAttr failed: invalid node in source={source}, destination={destination}")
        return

    src_attr = source.split(".")[-1]
    dst_attr = destination.split(".")[-1]

    src_path = f"{s_obj[0]}.{src_attr}"
    dst_path = f"{d_obj[0]}.{dst_attr}"
    logger.info(f"Connecting attribute {src_path} to {dst_path}")

    try:
        cmds.connectAttr(src_path, dst_path)
    except RuntimeError as e:
        logger.error(f"Connection failed from {src_path} to {dst_path}: {e}")


def parent_constrain(
    source,
    destination,
    mode,
    maintain_offset=True,
    translate_axis=("x", "y", "z"),
    rotate_axis=("x", "y", "z"),
    weight=None,
):
    # type: (OpenMaya2.MDagPath, Union[OpenMaya2.MDagPath, list[OpenMaya2.MDagPath]], Text, bool, tuple[Text, ...], tuple[Text, ...], Optional[float]) -> None
    """Create parent constraint between nodes.

    Args:
        source: Source transform node (MDagPath)
        destination: Destination transform node(s) (MDagPath or list)
        mode: Constraint mode ('t' for translate, 'r' for rotate, 's' for scale, or combination)
        maintain_offset: Whether to maintain the initial offset
        translate_axis: Which translation axes to constrain
        rotate_axis: Which rotation axes to constrain
        weight: Optional constraint weight
    """
    if isinstance(destination, list):
        for dest in destination:
            parent_constrain(source, dest, mode, maintain_offset, translate_axis, rotate_axis, weight)
        return

    skip_translate = ()
    skip_rotate = ()

    # Decide which channels to skip
    if mode:
        if "t" not in mode:
            skip_translate = ("x", "y", "z")
        if "r" not in mode:
            skip_rotate = ("x", "y", "z")

    # parentConstraint (translate/rotate)
    if not mode or "t" in mode or "r" in mode:
        cns_list = cmds.parentConstraint(
            source.fullPathName(),
            destination.fullPathName(),
            skipTranslate=skip_translate,  # type: ignore
            skipRotate=skip_rotate,  # type: ignore
            maintainOffset=maintain_offset,
        )
        if not cns_list:
            return

        cns_node = cns_list[0]  # type: ignore
        # interpType を 0 (平均) にする
        cmds.setAttr(f"{cns_node}.interpType", 0)

        # ウェイトが指定されていれば設定
        if weight is not None:
            attrs = cmds.listAttr(cns_node, keyable=True) or []  # type: ignore
            src_name = source.fullPathName().replace(":", "|").split("|")[-1]
            weight_attr = f"{src_name}W"
            for a in attrs:
                if weight_attr in a:
                    cmds.setAttr(f"{cns_node}.{a}", weight)

    # scaleConstraint
    if mode and "s" in mode:
        cmds.scaleConstraint(
            source.fullPathName(),
            destination.fullPathName(),
            maintainOffset=maintain_offset,
        )


##############################################################################
# Context Managers
##############################################################################
@contextlib.contextmanager
def maintain_children(target):
    # type: (str) -> Generator
    """Context manager that preserves child hierarchy during operations.

    Args:
        target: The node whose children to preserve

    Yields:
        None
    """
    children = cmds.listRelatives(target, children=True, fullPath=True, type="transform") or []
    world_children = []
    for child in children:
        world_children.extend(cmds.parent(child, world=True))

    try:
        yield
    finally:
        for child in world_children:
            cmds.parent(child, target)


##############################################################################
# Matching (do_match) & Connecting (do_connect)
##############################################################################


def __tokenize_offset(node, offset, mode="t"):
    # type: (str, Union[Text, list[Union[str, float]], tuple[Union[str, float], ...]], str) -> list[float]
    """Tokenize offset values, resolving any relative offsets like "2.5x".

    Args:
        node: Node to apply offset to (str)
        offset: Offset values or specifications
        mode: 't' for translation, 'r' for rotation

    Returns:
        List of float offset values
    """
    matrix = cmds.xform(node, query=True, os=True, matrix=True)
    m1 = OpenMaya2.MMatrix(matrix)
    m2 = OpenMaya2.MMatrix(matrix)

    # Zero out local translation
    m2.setElement(3, 0, 0.0)
    m2.setElement(3, 1, 0.0)
    m2.setElement(3, 2, 0.0)

    norm_mat = m1 * m2.inverse()
    norm_xform = OpenMaya2.MTransformationMatrix(norm_mat)
    norm_pos = norm_xform.translation(OpenMaya2.MSpace.kTransform)
    norm_rot = norm_xform.rotation().asVector()

    def _tokenize_value(val, idx):
        # e.g. "2.5x" means relative to local transform
        if isinstance(val, six.string_types) and val.endswith("x"):
            try:
                ratio = float(val[:-1])
                if mode == "t":
                    return norm_pos[idx] * ratio
                elif mode == "r":
                    return norm_rot[idx] * ratio
            except ValueError:
                logger.warning(f"Invalid ratio format: {val}")
                return 0.0
        # absolute value
        try:
            return float(val)
        except (ValueError, TypeError):
            logger.warning(f"Invalid offset value: {val}")
            return 0.0

    return [_tokenize_value(x, i) for i, x in enumerate(offset)]


def do_match(entry, selection=None, option=None, preserve_children=False):
    # type: (dict[Text, Any], Optional[list[Text]], Optional[MGOption], bool) -> None
    """Match transform of source node to destination node.

    Args:
        entry: Dict defining the match operation (must contain "src", "dst", etc.)
        selection: List of selected nodes to restrict operation to
        option: MGOption for alias handling, etc.
        preserve_children: Whether to preserve children hierarchies during match
    """
    s_query = util.displayable_path(entry["src"])
    d_query = util.displayable_path(entry["dst"])

    if not s_query:
        logger.debug(f"Skipping match, no source found in entry: {entry}")
        return

    if option and option.alias_definition is not None:
        if option.src_alias:
            s_query = apply_alias(s_query, option.alias_definition)
        if option.dst_alias:
            d_query = apply_alias(d_query, option.alias_definition)

    source = get_node(s_query)
    destination = get_node(d_query)

    if selection is not None and destination:
        # Check short name to see if it is in selection
        d_short_name = destination.fullPathName().split("|")[-1].split(":")[-1]
        if d_short_name not in selection:
            logger.debug(f"Skipping match, destination {d_short_name} not in selection.")
            return

    if not source or not destination:
        logger.debug(f"Skipping match, missing src or dst: {s_query}, {d_query}")
        return

    mode = entry.get("mode", ["t"])
    if isinstance(mode, six.string_types):
        mode = [mode]

    def _perform_match():
        logger.info(f"Matching mode({mode}) destination: {destination}, source: {source}")

        # Translation
        if "t" in mode:
            translation = get_translation(source)
            set_translation(destination, translation)

            t_offset = entry.get("t_offset")
            if t_offset:
                t_val = __tokenize_offset(destination.fullPathName(), t_offset, "t")
                cmds.move(t_val[0], t_val[1], t_val[2],
                          destination.fullPathName(),
                          os=True, relative=True, worldSpaceDistance=True)

        # Rotation
        if "r" in mode:
            try:
                quat = get_rotation(source)
                set_rotation(destination, quat)
                r_offset = entry.get("r_offset")
                if r_offset:
                    r_val = __tokenize_offset(destination.fullPathName(), r_offset, "r")
                    cmds.rotate(r_val[0], r_val[1], r_val[2],
                                destination.fullPathName(),
                                os=True, r=True)
            except TypeError:
                logger.exception("Error applying rotation match")

    if preserve_children:
        with maintain_children(destination.fullPathName()):
            _perform_match()
    else:
        _perform_match()


def do_connect(entry, option=None):
    # type: (dict[Text, Any], Optional[MGOption]) -> None
    """Connect or constrain one node to another.

    Args:
        entry: Dict defining the connection (contains "src", "dst", "mode", etc.)
        option: MGOption for alias handling, etc.
    """
    def _connect_single(src_query, dst_query, _mode, _weight=None):
        # type: (Text, Text, Text, Optional[float]) -> None
        if option and option.alias_definition:
            if option.src_alias:
                src_query = apply_alias(src_query, option.alias_definition)
            if option.dst_alias:
                dst_query = apply_alias(dst_query, option.alias_definition)

        dst_multi = option.dst_multiple if option else False

        source = get_node(src_query)
        if dst_multi:
            destination = get_node(dst_query)
        else:
            destination = get_nodes(dst_query)

        if not source or not destination:
            if not source:
                logger.error("Source node {0} for {1} not found.".format(src_query, entry.get("src")))
            if not destination:
                logger.error("Destination node {0} for {1} not found.".format(dst_query, entry.get("dst")))
            return

        if _mode == "a":
            # Attribute connection
            connect_attr(src_query, dst_query)
        else:
            # Parent constraint
            parent_constrain(source, destination, _mode, maintain_offset=True, weight=_weight)

    s_query = entry.get("src")  # type: Union[list[Any], Text]
    d_query = entry.get("dst")  # type: Text
    if not d_query:
        logger.error(f"No 'dst' found in entry: {entry}")
        return

    if isinstance(s_query, list):
        # Multiple sources
        for s_item in s_query:
            _src_name = s_item.get("src")
            _mode = s_item.get("mode", "srt")
            _weight = s_item.get("weight", None)
            _connect_single(_src_name, d_query, _mode, _weight)
    else:
        # Single source
        _mode = entry.get("mode", "srt")
        _connect_single(s_query, d_query, _mode)


##############################################################################
# Top-level Functions
##############################################################################


def match(def_file_name="test.yaml", domain="guide_on_bone", option=None):
    # type: (Text, Text, Optional[MGOption]) -> None
    """Match transforms based on configuration file.

    Args:
        def_file_name: YAML or JSON configuration file
        domain: Domain (key) to read from configuration
        option: MGOption for alias handling, etc.
    """
    try:
        match_entries = anyconfig.load(def_file_name)
        if not isinstance(match_entries, dict):
            raise ValueError(f"Config file does not contain a valid dict: {def_file_name}")

        selection = cmds.ls(sl=True)  # current selection

        for entry in match_entries.get(domain, []):
            logger.info(f"Processing entry: {entry}")

            do_match(entry, selection, option)
    except Exception as e:
        logger.error(f"Error in match operation: {e}")
        logger.exception("Traceback:")


def connect_on_deformer(def_file_name="test.yaml", domain="bone_on_deformer", option=None):
    # type: (Text, Text, Optional[MGOption]) -> None
    """Connect nodes based on configuration file.

    Args:
        def_file_name: YAML or JSON configuration file
        domain: Domain (key) to read from configuration
        option: MGOption for alias handling, etc.
    """
    try:
        config_map = anyconfig.load(def_file_name)
        if not config_map or not isinstance(config_map, dict):
            raise ValueError(f"Could not load config as dict from file: {def_file_name}")

        for entry in config_map.get(domain, []):
            try:
                do_connect(entry, option=option)
            except RuntimeError as ex:
                logger.error(f"Connection error for entry {entry}: {ex}")
    except Exception as e:
        logger.error(f"Error in connect_on_deformer: {e}")
        logger.exception("Traceback:")


##############################################################################
# Plug Utilities
##############################################################################

# e.g. "weights[0].influence"
plug_exp = re.compile(r"(?P<parent_name>\w+)\[(?P<parent_idx>\d+)\]\.(?P<target_name>\w+)")


def _get_plug(node, name):
    # type: (OpenMaya2.MFnDependencyNode, Text) -> Optional[OpenMaya2.MPlug]
    """Get a plug (attribute) from a node.

    Args:
        node: The node to get the plug from
        name: The name of the plug (could be array-like e.g. "attr[0].childAttr")

    Returns:
        The MPlug object or None if not found
    """
    if "." in name:
        match = plug_exp.match(name)
        if match:
            container_plug = node.findPlug(match.group("parent_name"), False)
            if container_plug.isArray:
                kid_attr = container_plug.attribute()
                kid_plug = node.findPlug(match.group("target_name"), False)
                kid_plug.selectAncestorLogicalIndex(int(match.group("parent_idx")), kid_attr)
                return kid_plug
    else:
        if not node.hasAttribute(name):
            return None
        try:
            return node.findPlug(name, False)
        except RuntimeError:
            logger.exception(f"Error getting plug {name} from {node.name()}")
            return None
    return None
