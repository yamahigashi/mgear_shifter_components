"""modifyed mgear.core.curve for adding matrix keyword arguments"""

#############################################
# GLOBAL
#############################################
import math
import six
import sys
try:
    import mgear.pymaya as pm
except ImportError:
    import pymel.core as pm
try:
    from mgear.pymaya import datatypes as dt
except ImportError:
    from pymel.core import datatypes as dt
import json

import maya.cmds as cmds
import maya.OpenMaya as om
import maya.api.OpenMaya as om2

from mgear.core import applyop
from mgear.core.transform import (
    getTransform,
)

from logging import (  # noqa:F401 pylint: disable=unused-import, wrong-import-order
    StreamHandler,
    getLogger,
    WARN,  # noqa: F401
    DEBUG,
    INFO
)

handler = StreamHandler()
handler.setLevel(DEBUG)
logger = getLogger(__name__)
logger.setLevel(INFO)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


if sys.version_info > (3, 0):
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from typing import (
            Optional,  # noqa: F401
            Dict,  # noqa: F401
            List,  # noqa: F401
            Tuple,  # noqa: F401
            Pattern,  # noqa: F401
            Callable,  # noqa: F401
            Any,  # noqa: F401
            Text,  # noqa: F401
            Generator,  # noqa: F401
            Iterable,  # noqa: F401
            Union  # noqa: F401
        )

#############################################
# CURVE
#############################################


def addCnsCurve(parent, name, drivers, degree=1, m=dt.Matrix(), close=False, local=False):
    """Create a curve attached to given drivers. One point per center

    Arguments:
        parent (dagNode): Parent object.
        name (str): Name
        drivers (list of dagNode): Object that will drive the curve.
        degree (int): 1 for linear curve, 3 for Cubic.

    Returns:
        dagNode: The newly created curve.
    """
    # rebuild list to avoid input list modification
    drivers = drivers[:]
    if degree == 3:
        if len(drivers) == 2:
            drivers.insert(0, drivers[0])
            drivers.append(drivers[-1])
        elif len(drivers) == 3:
            drivers.insert(1, drivers[1])

    for c in drivers:
        if isinstance(c, str):
            c = pm.PyNode(c)

    points = [dt.Vector() for center in drivers]

    node = addCurve(parent, name, points, degree=degree, m=m, close=close)

    if local:
        gear_curvecns_op_local(node, drivers)
    else:
        applyop.gear_curvecns_op(node, drivers)

    return node


def addCurve(parent,
             name,
             points,
             close=False,
             degree=3,
             m=dt.Matrix()):
    """Create a NurbsCurve with a single subcurve.

    Arguments:
        parent (dagNode): Parent object.
        name (str): Name
        positions (list of float): points of the curve in a one dimension array
            [point0X, point0Y, point0Z, 1, point1X, point1Y, point1Z, 1, ...].
        close (bool): True to close the curve.
        degree (bool): 1 for linear curve, 3 for Cubic.
        m (matrix): Global transform.

    Returns:
        dagNode: The newly created curve.
    """
    if close:
        points.extend(points[:degree])
        knots = range(len(points) + degree - 1)
        res = cmds.curve(n=name, d=degree, p=points, per=close, k=knots)
    else:
        res = cmds.curve(n=name, d=degree, p=points)

    node = pm.PyNode(res)

    if m is not None:
        node.setTransformation(m)

    if parent is not None:
        parent.addChild(node)

    return node


def createCurveFromOrderedEdges(edgeLoop,
                                startVertex,
                                name,
                                parent=None,
                                degree=3,
                                m=dt.Matrix(),
                                close=False):
    """Create a curve for a edgeloop ordering the list from starting vertex

    Arguments:
        edgeLoop (list ): List of edges
        startVertex (vertex): Starting vertex
        name (str): Name of the new curve.
        parent (dagNode): Parent of the new curve.
        degree (int): Degree of the new curve.

    Returns:
        dagNode: The newly created curve.
    """
    orderedEdges = []
    for e in edgeLoop:
        if startVertex in e.connectedVertices():
            orderedEdges.append(e)
            next = e
            break
    count = 0
    while True:
        for e in edgeLoop:
            if e in next.connectedEdges() and e not in orderedEdges:
                orderedEdges.append(e)
                next = e
                pass
        if len(orderedEdges) == len(edgeLoop):
            break
        count += 1
        if count > 100:
            break

    # return orderedEdges
    orderedVertex = [startVertex]
    startPos = startVertex.getPosition(space="world") 
    startPos = __applyInverseMatrixToPosition(startPos, m)
    orderedVertexPos = [startPos]
    for e in orderedEdges:

        for v in e.connectedVertices():
            if v not in orderedVertex:
                orderedVertex.append(v)
                pos = v.getPosition(space="world")
                pos = __applyInverseMatrixToPosition(pos, m)
         
                orderedVertexPos.append(pos)

    crv = addCurve(parent, name, orderedVertexPos, degree=degree, m=m, close=close)
    return crv


def createCurveFromEdges(edgeList,
                        name,
                        parent=None,
                        degree=3,
                        sortingAxis="x",
                        close=False,
                        m=dt.Matrix()):
    """Create curve from a edge list.

    Arguments:
        edgeList (list): List of edges.
        name (str): Name of the new curve.
        parent (dagNode): Parent of the new curve.
        degree (int): Degree of the new curve.
        sortingAxis (str): Sorting axis x, y or z

    Returns:
        dagNode: The newly created curve.

    """
    if "x" in sortingAxis:
        axis = 0
    elif "y" in sortingAxis:
        axis = 1
    else:
        axis = 2

    reverse = "-" in sortingAxis

    vList = pm.polyListComponentConversion(edgeList, fe=True, tv=True)

    centers = []
    centersOrdered = []
    xOrder = []
    xReOrder = []
    for x in vList:
        vtx = pm.PyNode(x)
        for v in vtx:
            centers.append(v.getPosition(space="world"))
            # we use index [0] to order in X axis
            xOrder.append(v.getPosition(space="world")[axis])
            xReOrder.append(v.getPosition(space="world")[axis])

    if reverse:
        xReOrder = sorted(xReOrder, reverse=True)
    else:
        xReOrder = sorted(xReOrder)

    for x in xReOrder:
        i = xOrder.index(x)
        point = centers[i]
        point = __applyInverseMatrixToPosition(point, m)
        centersOrdered.append(point)

    crv = addCurve(parent, name, centersOrdered, degree=degree, m=m, close=close)
    return crv


def __applyInverseMatrixToPosition(pos, m):
    # type: (list[float], dt.Matrix|om2.MMatrix|None) -> list[float]

    if m is None:
        return pos

    if isinstance(m, dt.Matrix):
        m = om2.MMatrix(m)

    translationMatrix = om2.MMatrix()
    translationMatrix.setToIdentity()
    translationMatrix[12] = pos[0]
    translationMatrix[13] = pos[1]
    translationMatrix[14] = pos[2]

    inv = m.inverse()

    mul = translationMatrix * inv
    res = [
        mul[12],
        mul[13],
        mul[14]
    ]

    return res


def createCurveFromCurve(srcCrv, name, nbPoints, parent=None, m=dt.Matrix(), close=False, space=om2.MSpace.kWorld):
    # type: (Union[str, pm.PyNode], str, int, Union[str, pm.PyNode, None], dt.Matrix, bool, str) -> pm.PyNode
    """Create a curve from a curve

    Arguments:
        srcCrv (curve): The source curve.
        name (str): The new curve name.
        nbPoints (int): Number of control points for the new curve.
        parent (dagNode): Parent of the new curve.
        m (matrix): Global transform.
        close (bool): True to close the curve.

    Returns:
        dagNode: The newly created curve.
    """

    sc = getMFnNurbsCurve(srcCrv)
    sc.updateCurve()

    length = sc.length()
    paramStart = sc.findParamFromLength(0.0)
    try:
        paramEnd = sc.findParamFromLength(length)
    except RuntimeError:
        paramEnd = sc.findParamFromLength(length - 0.001)
    paramLength = paramEnd - paramStart

    p = paramStart
    # if curve is close, we need to find start param to be offset to find nearest point to 0
    if close:
        increment = paramLength / nbPoints
        pos0 = sc.cvPosition(0)
        _, p = sc.closestPoint(pos0, space=om2.MSpace.kObject)

    else:
        increment = paramLength / nbPoints
        p = paramStart

    positions = []
    for i in range(nbPoints):
        point = sc.getPointAtParam(p, space=om2.MSpace.kWorld)
        point = __applyInverseMatrixToPosition(point, m)
        pos = (point[0], point[1], point[2])
        positions.append(pos)

        p += increment
        if p > paramEnd:

            if close:
                p -= paramLength
            else:
                p = paramEnd

    crv = addCurve(parent, name, positions, close=close, degree=3, m=m)
    return crv


def createCurveFromCurveEvenLength(srcCrv, name, nbPoints, parent=None, m=dt.Matrix(), close=False, space=om2.MSpace.kWorld):
    # type: (Union[str, pm.PyNode], str, int, Union[str, pm.PyNode, None], dt.Matrix, bool, str) -> pm.PyNode
    """Create a curve from a curve

    Arguments:
        srcCrv (curve): The source curve.
        name (str): The new curve name.
        nbPoints (int): Number of control points for the new curve.
        parent (dagNode): Parent of the new curve.
        m (matrix): Global transform.
        close (bool): True to close the curve.

    Returns:
        dagNode: The newly created curve.
    """

    if isinstance(srcCrv, six.string_types) or isinstance(srcCrv, six.text_type):
        srcCrv = pm.PyNode(srcCrv)

    cmds.dgeval(srcCrv.name())
    cmds.refresh()

    sc = getMFnNurbsCurve(srcCrv)
    sc.updateCurve()

    totalLength = sc.length()
    if close:
        cycleNb = nbPoints
    else:
        cycleNb = nbPoints - 1

    if close:
        pos0 = sc.cvPosition(0)
        _, p = sc.closestPoint(pos0)
        startLength = sc.findLengthFromParam(p)
    else:
        startLength = 0.0

    positions = []
    segmentLength = totalLength / cycleNb
    for i in range(nbPoints):
        length = segmentLength * i + startLength
        if length > totalLength:
            if close:
                length -= totalLength
            else:
                length = totalLength

        param = sc.findParamFromLength(length)
        pos = sc.getPointAtParam(param, space=space)
        pos = __applyInverseMatrixToPosition(pos, m)
        positions.append((pos[0], pos[1], pos[2]))

    crv = addCurve(parent, name, positions, close=close, degree=3, m=m)
    return crv


def getCurveParamAtPosition(crv, position):
    """Get curve parameter from a position

    Arguments:
        position (list of float): Represents the position in worldSpace
            exp: [1.4, 3.55, 42.6]
        crv (curve): The  source curve to get the parameter.

    Returns:
        list: paramenter and curve length
    """
    point = om.MPoint(position[0], position[1], position[2])

    dag = om.MDagPath()
    obj = om.MObject()
    oList = om.MSelectionList()
    oList.add(crv.name())
    oList.getDagPath(0, dag, obj)

    curveFn = om.MFnNurbsCurve(dag)
    length = curveFn.length()
    crv.findParamFromLength(length)

    paramUtill = om.MScriptUtil()
    paramPtr = paramUtill.asDoublePtr()

    point = curveFn.closestPoint(point, paramPtr, 0.001, om.MSpace.kObject)
    curveFn.getParamAtPoint(point, paramPtr, 0.001, om.MSpace.kObject)

    param = paramUtill.getDouble(paramPtr)

    return param, length


def getCurveParamByRatio(crv, ratio):
    """Get curve parameter from a ratio

    Arguments:
        crv (curve): The  source curve to get the parameter.
        ratio (float): Ratio on the curve

    Returns:
        list: paramenter and curve length
    """

    sc = getMFnNurbsCurve(crv.name())
    length = sc.length()
    paramStart = sc.findParamFromLength(0.0)
    paramEnd = sc.findParamFromLength(length)
    param = (paramEnd - paramStart) * ratio + paramStart

    return param, length


def getCurveLength(crv):
    # type: (str|dt.Transform|om2.MObject|om2.MDagPath|om2.MFnNurbsCurve) -> float
    """Get the length of a curve."""

    if not isinstance(crv, om2.MFnNurbsCurve):
        crv = getMFnNurbsCurve(crv)

    return crv.length()


def getPositionByRatio(crv, ratio):
    """Get position on curve from a ratio

    Arguments:
        crv (curve): The  source curve to get the parameter.
        ratio (float): Ratio on the curve

    Returns:
        float: position
    """
    param, length = getCurveParamByRatio(crv, ratio)
    point = crv.getShape().getPointAtParam(param, space='world')
    return point


def findLenghtFromParam(crv, param, close=False):
    """
    Find lengtht from a curve parameter

    Arguments:
        crv (curve): The source curve.
        param (float): The parameter to get the legth
        close (bool): If the curve is close or not.

    Returns:
        float: Curve uLength

    Example:
        .. code-block:: python

            oParam, oLength = cur.getCurveParamAtPosition(upRope, cv)
            uLength = cur.findLenghtFromParam(upRope, oParam)
            u = uLength / oLength

    """

    if close:
        sc = getMFnNurbsCurve(crv.name())
        return sc.findLengthFromParam(param)
    else:
        node = pm.createNode("arcLengthDimension")
        pm.connectAttr(
            crv.getShape().attr("worldSpace[0]"),
            node.attr("nurbsGeometry")
        )
        node.attr("uParamValue").set(param)
        uLength = node.attr("arcLength").get()
        pm.delete(node.getParent())
        return uLength


# ========================================

def get_color(node):
    """Get the color from shape node

    Args:
        node (TYPE): shape

    Returns:
        TYPE: Description
    """
    shp = node.getShape()
    if shp:
        if shp.overrideRGBColors.get():
            color = shp.overrideColorRGB.get()
        else:
            color = shp.overrideColor.get()

        return color


def set_color(node, color):
    """Set the color in the Icons.

    Arguments:
        node(dagNode): The object
        color (int or list of float): The color in index base or RGB.


    """
    # on Maya version.
    # version = mgear.core.getMayaver()

    if isinstance(color, int):

        for shp in node.listRelatives(shapes=True):
            shp.setAttr("overrideEnabled", True)
            shp.setAttr("overrideColor", color)
    else:
        for shp in node.listRelatives(shapes=True):
            shp.overrideEnabled.set(1)
            shp.overrideRGBColors.set(1)
            shp.overrideColorRGB.set(color[0], color[1], color[2])


# ========================================
# Curves IO ==============================
# ========================================

def collect_curve_shapes(crv, rplStr=["", ""]):
    """Collect curve shapes data

    Args:
        crv (dagNode): Curve object to collect the curve shapes data
        rplStr (list, optional): String to replace in names. This allow to
            change the curve names before store it.
            [old Name to replace, new name to set]

    Returns:
        dict, list: Curve shapes dictionary and curve shapes names
    """
    shapes_names = []
    shapesDict = {}
    for shape in crv.getShapes():
        shapes_names.append(shape.name().replace(rplStr[0], rplStr[1]))
        c_form = shape.form()
        degree = shape.degree()
        form = c_form.key
        form_id = c_form.index
        pnts = [[cv.x, cv.y, cv.z] for cv in shape.getCVs(space="object")]
        shapesDict[shape.name()] = {"points": pnts,
                                    "degree": degree,
                                    "form": form,
                                    "form_id": form_id}

    return shapesDict, shapes_names


def collect_selected_curve_data(objs=None):
    """Generate a dictionary descriving the curve data from selected objs

    Args:
        objs (None, optional): Optionally a list of object can be provided
    """
    if not objs:
        objs = pm.selected()

    return collect_curve_data(objs)


def collect_curve_data(objs, rplStr=["", ""]):
    """Generate a dictionary descriving the curve data

    Suport multiple objects

    Args:
        objs (dagNode): Curve object to store
        collect_trans (bool, optional): if false will skip the transformation
            matrix
        rplStr (list, optional): String to replace in names. This allow to
            change the curve names before store it.
            [old Name to replace, new name to set]

    Returns:
        dict: Curves data
    """

    # return if an empty list or None objects are pass
    if not objs:
        return

    if not isinstance(objs, list):
        objs = [objs]

    curves_dict = {}
    curves_dict["curves_names"] = []

    for x in objs:
        crv_name = x.name().replace(rplStr[0], rplStr[1])
        curves_dict["curves_names"].append(crv_name)
        if x.getParent():
            crv_parent = x.getParent().name().replace(rplStr[0], rplStr[1])
        else:
            crv_parent = None

        m = x.getMatrix(worldSpace=True)
        crv_transform = m.get()

        curveDict = {"shapes_names": [],
                     "crv_parent": crv_parent,
                     "crv_transform": crv_transform,
                     "crv_color": get_color(x)}

        shps, shps_n = collect_curve_shapes(x, rplStr)
        curveDict["shapes"] = shps
        curveDict["shapes_names"] = shps_n
        curves_dict[crv_name] = curveDict

    return curves_dict


def crv_parenting(data, crv, rplStr=["", ""], model=None):
    """Parent the new created curves

    Args:
        data (dict): serialized curve data
        crv (str): name of the curve to parent
        rplStr (list, optional): String to replace in names. This allow to
            change the curve names before store it.
            [old Name to replace, new name to set]
        model (dagNode, optional): Model top node to help find the correct
            parent, if  several objects with the same name
    """
    crv_dict = data[crv]
    crv_parent = crv_dict["crv_parent"]
    crv_p = None
    crv = crv.replace(rplStr[0], rplStr[1])
    parents = pm.ls(crv_parent)
    # this will try to find the correct parent by checking the top node
    # in situations where the name is reapet in many places under same
    # hierarchy this method will fail.
    if len(parents) > 1 and model:
        for p in parents:
            if model.name() in p.name():
                crv_p = p
                break
    elif len(parents) == 1:
        crv_p = parents[0]
    else:
        pm.displayWarning("More than one parent with the same name found for"
                          " {}, or not top model root provided.".format(crv))
        pm.displayWarning("This curve"
                          "  can't be parented. Please do it manually or"
                          " review the scene")
    if crv_p:
        # we need to ensure that we parent is the new curve.
        crvs = pm.ls(crv)
        if len(crvs) > 1:
            for c in crvs:
                if not c.getParent():  # if not parent means is the new
                    crv = c
                    break
        elif len(crvs) == 1:
            crv = crvs[0]
        pm.parent(crv,
                  crv_p)


def create_curve_from_data_by_name(crv,
                                   data,
                                   replaceShape=False,
                                   rebuildHierarchy=False,
                                   rplStr=["", ""],
                                   model=None):
    """Build one curve from a given curve data dict

    Args:
        crv (str): name of the crv to create
        data (dict): serialized curve data
        replaceShape (bool, optional): If True, will replace the shape on
            existing objects
        rebuildHierarchy (bool, optional): If True, will regenerate the
            hierarchy
        rplStr (list, optional): String to replace in names. This allow to
            change the curve names before store it.
            [old Name to replace, new name to set]
        model (dagNode, optional): Model top node to help find the correct
            parent, if  several objects with the same name
    """
    crv_dict = data[crv]

    crv_transform = crv_dict["crv_transform"]
    shp_dict = crv_dict["shapes"]
    color = crv_dict["crv_color"]
    if replaceShape:
        first_shape = pm.ls(crv.replace(rplStr[0], rplStr[1]))
        if first_shape and model and model == first_shape[0].getParent(-1):
            pass
        else:
            first_shape = None
    else:
        first_shape = None

    if first_shape:
        first_shape = first_shape[0]
        # clean old shapes
        pm.delete(first_shape.listRelatives(shapes=True))
    for sh in crv_dict["shapes_names"]:
        points = shp_dict[sh]["points"]
        form = shp_dict[sh]["form"]
        degree = shp_dict[sh]["degree"]
        knots = range(len(points) + degree - 1)
        if form != "open":
            close = True
        else:
            close = False

        # we dont use replace in order to support multiple shapes
        nsh = crv.replace(rplStr[0], rplStr[1])
        obj = pm.curve(name=nsh.replace("Shape", ""),
                       point=points,
                       periodic=close,
                       degree=degree,
                       knot=knots)
        set_color(obj, color)
        # handle multiple shapes in the same transform
        if not first_shape:
            first_shape = obj
            first_shape.setTransformation(crv_transform)
        else:
            for extra_shp in obj.listRelatives(shapes=True):
                first_shape.addChild(extra_shp, add=True, shape=True)
                pm.delete(obj)

    if rebuildHierarchy:
        crv_parenting(data, crv, rplStr, model)


def create_curve_from_data(data,
                           replaceShape=False,
                           rebuildHierarchy=False,
                           rplStr=["", ""],
                           model=None):
    """Build the curves from a given curve data dict

    Hierarchy rebuild after all curves are build to avoid lost parents

    Args:
        data (dict): serialized curve data
        replaceShape (bool, optional): If True, will replace the shape on
            existing objects
        rebuildHierarchy (bool, optional): If True, will regenerate the
            hierarchy
    """

    for crv in data["curves_names"]:
        create_curve_from_data_by_name(crv,
                                       data,
                                       replaceShape,
                                       rebuildHierarchy=False,
                                       rplStr=rplStr)

    # parenting
    if rebuildHierarchy:
        for crv in data["curves_names"]:
            crv_parenting(data, crv, rplStr, model)


def update_curve_from_data(data, rplStr=["", ""]):
    """update the curves from a given curve data dict

    Args:
        data (dict): serialized curve data
    """

    for crv in data["curves_names"]:
        crv_dict = data[crv]

        shp_dict = crv_dict["shapes"]
        color = crv_dict["crv_color"]
        first_shape = pm.ls(crv.replace(rplStr[0], rplStr[1]))
        if not first_shape:
            pm.displayWarning("Couldn't find: {}. Shape will be "
                              "skipped, since there is nothing to "
                              "replace".format(crv.replace(rplStr[0],
                                                           rplStr[1])))
            continue

        if first_shape:
            first_shape = first_shape[0]
            # Because we don know if the number of shapes will match between
            # the old and new shapes. We only take care of the connections
            # of the first shape. Later will be apply to all the new shapes

            # store shapes connections
            shapes = first_shape.listRelatives(shapes=True)
            if shapes:
                cnx = shapes[0].listConnections(plugs=True, c=True)
                cnx = [[c[1], c[0].shortName()] for c in cnx]
                # Disconnect the conexion before delete the old shapes
                for s in shapes:
                    for c in s.listConnections(plugs=True, c=True):
                        pm.disconnectAttr(c[0])
                # clean old shapes
                pm.delete(shapes)

        for sh in crv_dict["shapes_names"]:
            points = shp_dict[sh]["points"]
            form = shp_dict[sh]["form"]
            degree = shp_dict[sh]["degree"]
            knots = range(len(points) + degree - 1)
            if form != "open":
                close = True
            else:
                close = False
            # we dont use replace in order to support multiple shapes
            obj = pm.curve(replace=False,
                           name=sh.replace(rplStr[0], rplStr[1]),
                           point=points,
                           periodic=close,
                           degree=degree,
                           knot=knots)
            set_color(obj, color)
            for extra_shp in obj.listRelatives(shapes=True):
                # Restore shapes connections
                for c in cnx:
                    pm.connectAttr(c[0], extra_shp.attr(c[1]))
                first_shape.addChild(extra_shp, add=True, shape=True)
                pm.delete(obj)

        # clean up shapes names
        for sh in first_shape.getShapes():
            pm.rename(sh, sh.name().replace("ShapeShape", "Shape"))


def export_curve(filePath=None, objs=None):
    """Export the curve data to a json file

    Args:
        filePath (None, optional): Description
        objs (None, optional): Description

    Returns:
        TYPE: Description
    """

    if not filePath:
        startDir = pm.workspace(q=True, rootDirectory=True)
        filePath = pm.fileDialog2(
            dialogStyle=2,
            fileMode=0,
            startingDirectory=startDir,
            fileFilter='NURBS Curves .crv (*%s)' % ".crv")
        if not filePath:
            pm.displayWarning("Invalid file path")
            return
        if not isinstance(filePath, (six.string_types, six.text_type)):
            filePath = filePath[0]

    data = collect_selected_curve_data(objs)
    data_string = json.dumps(data, indent=4, sort_keys=True)
    f = open(filePath, 'w')
    f.write(data_string)
    f.close()


def _curve_from_file(filePath=None):
    if not filePath:
        startDir = pm.workspace(q=True, rootDirectory=True)
        filePath = pm.fileDialog2(
            dialogStyle=2,
            fileMode=1,
            startingDirectory=startDir,
            fileFilter='NURBS Curves .crv (*%s)' % ".crv")

    if not filePath:
        pm.displayWarning("Invalid file path")
        return
    if not isinstance(filePath, (six.string_types, six.text_type)):
        filePath = filePath[0]
    configDict = json.load(open(filePath))

    return configDict


def import_curve(filePath=None,
                 replaceShape=False,
                 rebuildHierarchy=False,
                 rplStr=["", ""]):
    create_curve_from_data(_curve_from_file(filePath),
                           replaceShape,
                           rebuildHierarchy,
                           rplStr)


def update_curve_from_file(filePath=None, rplStr=["", ""]):
    # update a curve data from json file
    update_curve_from_data(_curve_from_file(filePath), rplStr)


def getMFnNurbsCurve(crv):

    if isinstance(crv, six.string_types) or isinstance(crv, six.text_type):
        dag = as_dagpath(crv)
    else:
        dag = as_dagpath(crv.name())

    curveFn = om2.MFnNurbsCurve(dag)
    return curveFn


def as_selection_list(iterable):
    # type: (Iterable) -> om2.MSelectionList

    selectionList = om2.MSelectionList()
    for each in iterable:
        selectionList.add(each)
    return selectionList


def as_dagpath_list(iterable):
    # type: (Iterable) -> Generator[om2.MDagPath, None, None]
    selectionList = as_selection_list(iterable)
    for i in range(selectionList.length()):
        yield selectionList.getDagPath(i)


def as_dagpath(name):
    # type: (Text) -> om2.MDagPath
    selectionList = as_selection_list([name])

    try:
        return selectionList.getDagPath(0)
    except:
        return selectionList.getDependNode(0)


def as_dependnode(name):
    # type: (Text) -> om2.MFnDependencyNode
    selectionList = as_selection_list([name])
    return om2.MFnDependencyNode(selectionList.getDependNode(0))


def as_dependencynodes(iterable):
    # type: (Iterable) -> List[om2.MFnDependencyNode]
    selectionList = as_selection_list(iterable)
    for i in range(selectionList.length()):
        yield om2.MFnDependencyNode(selectionList.getDagPath(i).node())


def as_dependencynode(name):
    # type: (Text) -> om2.MFnDependencyNode
    dagpath = as_dagpath(name)
    return om2.MFnDependencyNode(dagpath.node())


def as_mfn_mesh(name):
    # type: (Text) -> om2.MFnMesh
    dagpath = as_dagpath(name)
    return om2.MFnMesh(dagpath.node())


def as_mfnmesh(name):
    # type: (Text) -> om2.MFnMesh
    dagpath = as_dagpath(name)
    return om2.MFnMesh(dagpath)


def applyPathCnsLocal(target, curve, u, maintainOffset=True):
    # type: (dt.Transform, dt.Transform, float, bool) -> "motionPath"
    import ymt_shifter_utility

    # prev_matrix = target.getMatrix(objectSpace=True)
    ma = target.getMatrix(worldSpace=True)
    mb = curve.getMatrix(worldSpace=True)

    cns = applyop.pathCns(target, curve, cnsType=False, u=u, tangent=False)

    # TODO: extract axis into arguments
    cmds.setAttr(cns + ".worldUpType", 2)  # object rotation up
    cmds.setAttr(cns + ".worldUpVectorX", 0)
    cmds.setAttr(cns + ".worldUpVectorY", 1)
    cmds.setAttr(cns + ".worldUpVectorZ", 0)
    cmds.connectAttr(curve.longName() + ".matrix", cns + ".worldUpMatrix")  # object rotation up
    cmds.setAttr(cns + ".frontAxis", 2)  # front axis x
    cmds.setAttr(cns + ".upAxis", 1)  # up axis y
    pm.connectAttr(curve.attr("local"), cns.attr("geometryPath"), f=True)

    comp_node = pm.createNode("composeMatrix")
    cns.attr("allCoordinates") >> comp_node.attr("inputTranslate")  # pyright: ignore [reportUnusedExpression]
    cns.attr("rotate") >> comp_node.attr("inputRotate")  # pyright: ignore [reportUnusedExpression]
    cns.attr("rotateOrder") >> comp_node.attr("inputRotateOrder")  # pyright: ignore [reportUnusedExpression]

    tmp_output = dt.Matrix(comp_node.attr("outputMatrix").get())
    tmp_global = tmp_output * mb
    offset_matrix = om2.MMatrix(ma * tmp_global.inverse())

    if maintainOffset:
        start_index = 1
    else:
        start_index = 0

    mul_node = pm.createNode("multMatrix")
    comp_node.attr("outputMatrix") >> mul_node.attr("matrixIn[{}]".format(start_index))  # pyright: ignore [reportUnusedExpression]

    down, _, up = ymt_shifter_utility.findPathAtoB(curve, target)
    i = 0
    j = 0
    for _i, _d in enumerate(down):
        i = _i
        _d.attr("matrix") >> mul_node.attr("matrixIn[{}]".format(start_index + i + 1))  # pyright: ignore [reportUnusedExpression]

    for j, _u in enumerate(up[:-1]):
        _u.attr("inverseMatrix") >> mul_node.attr("matrixIn[{}]".format(start_index + i + j + 2))  # pyright: ignore [reportUnusedExpression]

    if maintainOffset:
        tmp_output = mul_node.attr("matrixSum").get()
        offset_node = pm.createNode("fourByFourMatrix")
        offset_node.attr("in00").set(offset_matrix[0])
        offset_node.attr("in01").set(offset_matrix[1])
        offset_node.attr("in02").set(offset_matrix[2])
        offset_node.attr("in03").set(offset_matrix[3])
        offset_node.attr("in10").set(offset_matrix[4])
        offset_node.attr("in11").set(offset_matrix[5])
        offset_node.attr("in12").set(offset_matrix[6])
        offset_node.attr("in13").set(offset_matrix[7])
        offset_node.attr("in20").set(offset_matrix[8])
        offset_node.attr("in21").set(offset_matrix[9])
        offset_node.attr("in22").set(offset_matrix[10])
        offset_node.attr("in23").set(offset_matrix[11])
        offset_node.attr("in30").set(offset_matrix[12])
        offset_node.attr("in31").set(offset_matrix[13])
        offset_node.attr("in32").set(offset_matrix[14])
        offset_node.attr("in33").set(offset_matrix[15])
        offset_node.attr("output") >> mul_node.attr("matrixIn[0]")  # pyright: ignore [reportUnusedExpression]

    decomp_node = pm.createNode("decomposeMatrix")
    mul_node.attr("matrixSum") >> decomp_node.attr("inputMatrix")  # pyright: ignore [reportUnusedExpression]
    decomp_node.attr("outputTranslate") >> target.attr("translate")  # pyright: ignore [reportUnusedExpression]
    decomp_node.attr("outputRotate") >> target.attr("rotate")  # pyright: ignore [reportUnusedExpression]

    return cns
    

def applyPathConstrainLocal(target, src_curve, maintainOffset=True):
    # type: (str, str) -> None

    if isinstance(target, six.string_types) or isinstance(target, six.text_type):
        target = pm.PyNode(target)
    if isinstance(src_curve, six.string_types) or isinstance(src_curve, six.text_type):
        src_curve = pm.PyNode(src_curve)

    try:
        ma = target.getMatrix(worldSpace=True)
        mb = src_curve.getMatrix(worldSpace=True)
        m = om2.MMatrix(ma * mb.inverse())
        pos = dt.Vector(m[12], m[13], m[14])
        param, length = getCurveParamAtPosition(src_curve, pos)
        u_length = findLenghtFromParam(src_curve, param)
        u_param = u_length / length

        cns = applyPathCnsLocal(target, src_curve, u_param, maintainOffset)
    except:
        import traceback as tb
        tb.print_exc()
        raise

    return cns


def applyRopeCnsLocal(target, ctl_curve, rope, cv):

    def _searchNearestEditPoint(curve, cv):

        candidate = math.inf
        index = 0
        numberOfSpans = cmds.getAttr(curve + ".spans")

        for i in range(numberOfSpans):
            point = cmds.getAttr(curve + ".editPoints["+str(i)+"]")[0]
            dist = math.sqrt((point[0] - cv[0])**2 + (point[1] - cv[1])**2 + (point[2] - cv[2])**2)
            if dist < candidate:
                candidate = dist
                index = i

        return index

    nearestIndex = _searchNearestEditPoint(rope, cv)

    nearestPointOnCurve = cmds.createNode("nearestPointOnCurve")
    cmds.connectAttr(rope+ ".editPoints["+str(nearestIndex)+"]", nearestPointOnCurve + ".inPosition")
    cmds.connectAttr(rope + ".local", nearestPointOnCurve + ".inputCurve")

    motionPath = cmds.createNode("motionPath")
    cmds.connectAttr(nearestPointOnCurve + ".parameter", motionPath + ".uValue")
    cmds.connectAttr(rope + ".local", motionPath + ".geometryPath")

    cmds.setAttr(motionPath + ".fractionMode", 0)
    cmds.setAttr(motionPath + ".frontAxis", 0)
    cmds.setAttr(motionPath + ".worldUpType", 2)
    cmds.setAttr(motionPath + ".worldUpVector", 0, 1, 0)
    cmds.connectAttr(ctl_curve.longName() + ".matrix", motionPath + ".worldUpMatrix")  # object rotation up
    cmds.setAttr(motionPath + ".frontAxis", 0)
    cmds.setAttr(motionPath + ".upAxis", 2)

    cmds.connectAttr(nearestPointOnCurve + ".position", target.longName() + ".translate")
    cmds.connectAttr(motionPath + ".rotate", target.longName() + ".rotate")


def applyRopeCnsLocalWithUpv(target, upv, ctl_curve, rope, cv):
    # type: (dt.Transform, dt.Transform, dt.Transform, dt.Transform, om2.MPoint) -> None
    """Apply a rope constraint to a target object.

    Arguments:
        target (dt.Transform): The target object to constraint.
        upv (dt.Transform): The up vector object.
        ctl_curve (dt.Transform): The control curve object.
        rope (dt.Transform): The rope object.
        cv (dt.Vector): The control vertex position.

    Returns:
        None
    """

    def _searchNearestEditPoint(curve, cv):

        candidate = math.inf
        index = 0
        numberOfSpans = cmds.getAttr(curve + ".spans")

        for i in range(numberOfSpans):
            point = cmds.getAttr(curve + ".editPoints["+str(i)+"]")[0]
            dist = math.sqrt((point[0] - cv[0])**2 + (point[1] - cv[1])**2 + (point[2] - cv[2])**2)
            if dist < candidate:
                candidate = dist
                index = i

        return index

    nearestIndex = _searchNearestEditPoint(rope, cv)

    nearestPointOnCurve = cmds.createNode("nearestPointOnCurve")
    cmds.connectAttr(rope+ ".editPoints["+str(nearestIndex)+"]", nearestPointOnCurve + ".inPosition")
    cmds.connectAttr(rope + ".local", nearestPointOnCurve + ".inputCurve")

    motionPath = cmds.createNode("motionPath")
    cmds.connectAttr(nearestPointOnCurve + ".parameter", motionPath + ".uValue")
    cmds.connectAttr(rope + ".local", motionPath + ".geometryPath")

    cmds.setAttr(motionPath + ".fractionMode", 0)

    cmds.connectAttr(nearestPointOnCurve + ".position", target.longName() + ".translate")
    _cns = cmds.aimConstraint(
        upv.longName(),
        target.longName(),
        maintainOffset=False,
        aimVector=(0, 0, 1),
        upVector=(1, 0, 0),
        worldUpType="objectrotation",
        worldUpObject=upv.longName(),
        worldUpVector=(1, 0, 0)
    )


def curvecns_op(crv, inputs=[]):

    for i, item in enumerate(inputs):
        node = pm.createNode("decomposeMatrix")
        pm.connectAttr(item + ".worldMatrix[0]", node + ".inputMatrix")
        pm.connectAttr(node + ".outputTranslate",
                       crv + ".controlPoints[%s]" % i)

    return node


def gear_curvecns_op(crv, inputs=[]):
    """
    create mGear curvecns node.

    Arguments:
        crv (nurbsCurve): Nurbs curve.
        inputs (List of dagNodes): Input object to drive the curve. Should be
            same number as crv points.
            Also the order should be the same as the points

    Returns:
        pyNode: The curvecns node.
    """
    pm.select(crv)
    node = pm.deformer(type="mgear_curveCns")[0]

    for i, item in enumerate(inputs):
        pm.connectAttr(item + ".worldMatrix", node + ".inputs[%s]" % i)

    return node


def gear_curvecns_op_local(crv, inputs=[]):
    """
    create mGear curvecns node.

    Arguments:
        crv (nurbsCurve): Nurbs curve.
        inputs (List of dagNodes): Input object to drive the curve. Should be
            same number as crv points.
            Also the order should be the same as the points

    Returns:
        pyNode: The curvecns node.
    """
    import ymt_shifter_utility

    pm.select(crv)
    deformer_name = cmds.deformer(type="mgear_curveCns")[0]

    con = cmds.listConnections(deformer_name + ".input", plugs=True, connections=True, source=True, destination=False)
    dst, src = con

    cmds.disconnectAttr(src, dst)
    cmds.connectAttr(
        src.split(".")[0] + ".local",
        deformer_name + ".input[0].inputGeometry"
    )

    for i, item in enumerate(inputs):
        localMat = ymt_shifter_utility.getMultMatrixOfAtoB(item, crv, skip_last=False)
        pm.connectAttr(localMat + ".matrixSum", deformer_name + ".inputs[%s]" % i)

    return deformer_name


def gear_curvecns_op_local_skip_rotate(crv, inputs=[]):
    """."""

    deformer_name = gear_curvecns_op_local(crv, inputs)
    inputs = cmds.listAttr(deformer_name + ".inputs", multi=True)
    for input_path in inputs:
        mult = cmds.listConnections(
            deformer_name + "." + input_path,
            source=True,
            destination=False)[0]

        ctl = cmds.listConnections(
                mult + ".matrixIn[0]",
                source=True,
                destination=False)[0]

        cmds.disconnectAttr(
            ctl + ".matrix",
            mult + ".matrixIn[0]"
        )

        compMat = cmds.createNode("composeMatrix")
        cmds.connectAttr(
            ctl + ".translate",
            compMat + ".inputTranslate"
        )
        cmds.connectAttr(
            compMat + ".outputMatrix",
            mult + ".matrixIn[0]"
        )

    return deformer_name


def createCurveOnSurfaceFromCurve(crv, surface, name):

    import ymt_shifter_utility

    src_crv = getMFnNurbsCurve(crv)
    close = src_crv.form == 3
    nbPoints = src_crv.numCVs + src_crv.degree

    t = getTransform(crv)
    targetCrv = createCurveFromCurve(
        crv.longName(),
        name,
        nbPoints=nbPoints,
        close=close,
        parent=crv.getParent(),
        m=t
    )

    localMat = ymt_shifter_utility.getMultMatrixOfAtoB(crv, surface, skip_last=True)
    invLocal = pm.createNode("inverseMatrix")
    pm.connectAttr(localMat + ".matrixSum", invLocal + ".inputMatrix")

    for pointNumber in range(nbPoints):
        compMat = pm.createNode("composeMatrix")
        pm.connectAttr(
            crv + ".editPoints[%s]" % pointNumber,
            compMat + ".inputTranslate"
        )

        # Mult matrix, change curve point position to surface local space
        multMat = pm.createNode("multMatrix")
        pm.connectAttr(
            compMat + ".outputMatrix",
            multMat + ".matrixIn[1]"
        )
        pm.connectAttr(
            localMat + ".matrixSum",
            multMat + ".matrixIn[0]"
        )

        decomposeMat = pm.createNode("decomposeMatrix")
        pm.connectAttr(
            multMat + ".matrixSum",
            decomposeMat + ".inputMatrix"
        )

        # Closest point on surface in local space
        closestPoint = pm.createNode("closestPointOnSurface")
        pm.connectAttr(
            decomposeMat + ".outputTranslate",
            closestPoint + ".inPosition"
        )

        pm.connectAttr(
            surface + ".local",
            closestPoint + ".inputSurface"
        )

        # apply inverse matrix to get the position in curve local space
        multMat2 = pm.createNode("multMatrix")
        compMat2 = pm.createNode("composeMatrix")
        decomposeMat2 = pm.createNode("decomposeMatrix")

        pm.connectAttr(
            closestPoint + ".position",
            compMat2 + ".inputTranslate"
        )
        pm.connectAttr(
            compMat2 + ".outputMatrix",
            multMat2 + ".matrixIn[0]"
        )
        pm.connectAttr(
            invLocal + ".outputMatrix",
            multMat2 + ".matrixIn[1]"
        )
        pm.connectAttr(
            multMat2 + ".matrixSum",
            decomposeMat2 + ".inputMatrix"
        )

        # Apply to curve
        pm.connectAttr(
            decomposeMat2 + ".outputTranslate",
            targetCrv + ".controlPoints[%s]" % pointNumber
        )

    return targetCrv


def gear_curvecns_op(crv, inputs=[]):
    """
    create mGear curvecns node.

    Arguments:
        crv (nurbsCurve): Nurbs curve.
        inputs (List of dagNodes): Input object to drive the curve. Should be
            same number as crv points.
            Also the order should be the same as the points

    Returns:
        pyNode: The curvecns node.
    """
    pm.select(crv)
    node = pm.deformer(type="mgear_curveCns")[0]

    for i, item in enumerate(inputs):
        pm.connectAttr(item + ".worldMatrix", node + ".inputs[%s]" % i)

    return node


def applyCurveParamCns(src, target):
    # type: (dt.Transform, dt.Transform) -> None

    if isinstance(src, six.string_types) or isinstance(src, six.text_type):
        src = pm.PyNode(src)

    if isinstance(target, six.string_types) or isinstance(target, six.text_type):
        target = pm.PyNode(target)

    numPoints = cmds.getAttr(target + ".controlPoints", size=True)

    src_crv = getMFnNurbsCurve(src)
    tgt_crv = getMFnNurbsCurve(target)

    src_length = src_crv.length()
    target_length = tgt_crv.length()

    for i in range(numPoints):
        pos = cmds.pointPosition(target + ".controlPoints[%s]" % i, local=True)
        param, length = getCurveParamAtPosition(target, pos)
        ratio = param / target_length
        new_param = src_crv.findParamFromLength(src_length * ratio)

        pointOnCurveInfo = cmds.createNode("pointOnCurveInfo")
        cmds.connectAttr(src + ".local", pointOnCurveInfo + ".inputCurve")
        cmds.setAttr(pointOnCurveInfo + ".parameter", new_param)
        cmds.connectAttr(pointOnCurveInfo + ".position", target + ".controlPoints[%s]" % i, force=True)


def getCvParamRatio(crv):
    # type: (str) -> list[float]
    """Return the ratio of each control point in a curve"""

    sc = getMFnNurbsCurve(crv)
    sc.updateCurve()

    length = sc.length()
    paramStart = sc.findParamFromLength(0.0)
    try:
        paramEnd = sc.findParamFromLength(length)
    except RuntimeError:
        paramEnd = sc.findParamFromLength(length - 0.001)

    paramLength = paramEnd - paramStart

    ratios = []
    for pos in sc.cvPositions():
        closest = sc.closestPoint(pos)[0]
        param = sc.getParamAtPoint(closest)
        ratio = (param - paramStart) / paramLength
        ratios.append(ratio)

    return ratios


def getCvLengthRatio(crv):
    # type: (str) -> list[float]
    """Return the ratio of each control point in a curve"""

    sc = getMFnNurbsCurve(crv)
    sc.updateCurve()

    totalLength = sc.length()
    paramStart = sc.findParamFromLength(0.0)
    try:
        paramEnd = sc.findParamFromLength(totalLength)
    except RuntimeError:
        paramEnd = sc.findParamFromLength(totalLength - 0.001)

    paramLength = paramEnd - paramStart

    ratios = []
    for pos in sc.cvPositions():
        closest = sc.closestPoint(pos)[0]
        param = sc.getParamAtPoint(closest)
        length = sc.findLengthFromParam(param)
        try:
            ratio = length / totalLength
        except ZeroDivisionError:
            ratio = 0.0
        ratios.append(ratio)

    return ratios


def setCvParamRatio(crv, ratios):
    # type: (str, list[float]) -> None
    """Set the ratio of each control point in a curve"""

    sc = getMFnNurbsCurve(crv)
    sc.updateCurve()

    length = sc.length()
    paramStart = sc.findParamFromLength(0.0)
    try:
        paramEnd = sc.findParamFromLength(length)
    except RuntimeError:
        paramEnd = sc.findParamFromLength(length - 0.001)

    newPositions = []
    for ratio in ratios:
        param = sc.findParamFromLength(ratio * length)
        point = sc.getPointAtParam(param, space=om2.MSpace.kObject)
        newPositions.append(point)

    sc.setCVPositions(newPositions)
    sc.updateCurve()


def getCenterPosition(crv, sampleCount=100):
    # type: (str) -> om2.MPoint

    sc = getMFnNurbsCurve(crv)
    sc.updateCurve()

    length = sc.length()
    paramStart = sc.findParamFromLength(0.0)
    try:
        paramEnd = sc.findParamFromLength(length)
    except RuntimeError:
        paramEnd = sc.findParamFromLength(length - 0.001)

    paramLength = paramEnd - paramStart

    points = []
    for i in range(sampleCount):
        param = paramStart + (paramLength / sampleCount) * i
        point = sc.getPointAtParam(param, space=om2.MSpace.kObject)
        points.append(point)

    return om2.MPoint(
        sum([p.x for p in points]) / sampleCount,
        sum([p.y for p in points]) / sampleCount,
        sum([p.z for p in points]) / sampleCount
    )
