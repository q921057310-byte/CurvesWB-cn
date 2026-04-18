# SPDX-License-Identifier: LGPL-2.1-or-later

__title__ = "B 样条转脚本"
__author__ = "Christophe Grellier (Chris_G)"
__license__ = "LGPL 2.1"
__doc__ = "生成用于构建所选 B 样条（BSpline）或贝塞尔（Bezier）几何体的 Python 脚本。"
__usage__ = """在 3D 视图中选择一些贝塞尔或 B 样条曲线/曲面，然后激活此工具。
所选的曲线或曲面将通过 Python 控制台中的命令重新创建。"""
import os
import FreeCAD
import FreeCADGui
import Part
from freecad.Curves import ICONPATH

TOOL_ICON = os.path.join(ICONPATH, 'curve_to_console.svg')


def nurbs_to_script(i, c):
    com = ["import FreeCAD",
           "from FreeCAD import Vector",
           "import Part", ""]
    if isinstance(c, Part.BSplineCurve):
        com.append("poles{} = {}".format(i, c.getPoles()))
        com.append("weights{} = {}".format(i, c.getWeights()))
        com.append("knots{} = {}".format(i, c.getKnots()))
        com.append("mults{} = {}".format(i, c.getMultiplicities()))
        com.append("periodic{} = {}".format(i, c.isPeriodic()))
        com.append("degree{} = {}".format(i, c.Degree))
        com.append("rational{} = {}".format(i, c.isRational()))
        com.append("bs{} = Part.BSplineCurve()".format(i))
        com.append("bs{}.buildFromPolesMultsKnots(poles{}, mults{}, knots{}, periodic{}, degree{}, weights{}, rational{})".format(i, i, i, i, i, i, i, i))
        com.append('obj{} = FreeCAD.ActiveDocument.addObject("Part::Spline","BSplineCurve{}")'.format(i, i))
        com.append("obj{}.Shape = bs{}.toShape()".format(i, i))
    elif isinstance(c, Part.BezierCurve):
        com.append("poles{} = {}".format(i, c.getPoles()))
        com.append("be{} = Part.BezierCurve()".format(i))
        com.append("be{}.increase({})".format(i, c.Degree))
        com.append("be{}.setPoles(poles{})".format(i, i))
        if c.isRational():
            w = c.getWeights()
            for j in range(len(w)):
                com.append("be{}.setWeight({},{})".format(i, j + 1, w[j]))
        com.append('obj{} = FreeCAD.ActiveDocument.addObject("Part::Spline","BezierCurve{}")'.format(i, i))
        com.append("obj{}.Shape = be{}.toShape()".format(i, i))
    elif isinstance(c, Part.BSplineSurface):
        com.append("poles{} = {}".format(i, c.getPoles()))
        com.append("umults{} = {}".format(i, c.getUMultiplicities()))
        com.append("vmults{} = {}".format(i, c.getVMultiplicities()))
        com.append("uknots{} = {}".format(i, c.getUKnots()))
        com.append("vknots{} = {}".format(i, c.getVKnots()))
        com.append("uperiodic{} = {}".format(i, c.isUPeriodic()))
        com.append("vperiodic{} = {}".format(i, c.isVPeriodic()))
        com.append("udegree{} = {}".format(i, c.UDegree))
        com.append("vdegree{} = {}".format(i, c.VDegree))
        com.append("weights{} = {}".format(i, c.getWeights()))
        com.append("bsp{} = Part.BSplineSurface()".format(i))
        com.append("bsp{}.buildFromPolesMultsKnots(poles{}, umults{}, vmults{},uknots{},vknots{},uperiodic{},vperiodic{}, udegree{}, vdegree{}, weights{})".format(i, i, i, i, i, i, i, i, i, i, i))
        #com.append("Part.show(bsp.toShape(), 'BSplineSurface{}')".format(i))
        com.append('obj{} = FreeCAD.ActiveDocument.addObject("Part::Spline","BSplineSurface{}")'.format(i, i))
        com.append("obj{}.Shape = bsp{}.toShape()".format(i, i))
    elif isinstance(c, Part.BezierSurface):
        com.append("poles{} = {}".format(i, c.getPoles()))
        com.append("uperiodic{} = {}".format(i, c.isUPeriodic()))
        com.append("vperiodic{} = {}".format(i, c.isVPeriodic()))
        com.append("udegree{} = {}".format(i, c.UDegree))
        com.append("vdegree{} = {}".format(i, c.VDegree))
        com.append("weights{} = {}".format(i, c.getWeights()))
        com.append("bsp{} = Part.BezierSurface()".format(i))
        com.append("bsp{}.increase(udegree{}, vdegree{})".format(i, i, i))
        # com.append("bsp{}.setUPeriodic(uperiodic{})".format(i, i))
        # com.append("bsp{}.setVPeriodic(vperiodic{})".format(i, i))
        for j in range(c.UDegree + 1):
            com.append("bsp{}.setPoleRow({}, poles{}[{}])".format(i, j + 1, i, j))
            com.append("bsp{}.setWeightRow({}, weights{}[{}])".format(i, j + 1, i, j))
        com.append('obj{} = FreeCAD.ActiveDocument.addObject("Part::Spline","BezierSurface{}")'.format(i, i))
        com.append("obj{}.Shape = bsp{}.toShape()".format(i, i))
    com.append("")

    for s in com:
        FreeCADGui.doCommand(s)


class NurbsToConsole:
    "将选定的 B 样条曲线（BSpline）输出到 Python 控制台"
    def GetResources(self):
        return {'Pixmap': TOOL_ICON,
                'MenuText': "B 样条曲线转控制台",
                'Accel': "",
                'ToolTip': "{}<br><br><b>用法：</b><br>{}".format(__doc__, "<br>".join(__usage__.splitlines()))}

    def Activated(self):
        s = FreeCADGui.Selection.getSelectionEx()
        i = 0
        for so in s:
            for sso in so.SubObjects:
                geom = ""
                if hasattr(sso, "Curve"):
                    geom = sso.Curve
                elif hasattr(sso, "Surface"):
                    geom = sso.Surface
                if ("Bezier" in str(geom)) or ("BSpline" in str(geom)):
                    nurbs_to_script(i, geom)
                    i += 1
        if i == 0:
            FreeCAD.Console.PrintError("{} :\n{}\n".format(__title__, __usage__))

    def IsActive(self):
        if FreeCAD.ActiveDocument:
            return True
        else:
            return False


FreeCADGui.addCommand('Curves_bspline_to_console', NurbsToConsole())
