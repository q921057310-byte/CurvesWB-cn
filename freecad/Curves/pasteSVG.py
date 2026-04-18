# SPDX-License-Identifier: LGPL-2.1-or-later

__title__ = "粘贴 SVG"
__author__ = "Christophe Grellier (Chris_G)"
__license__ = "LGPL 2.1"
__doc__ = "粘贴剪贴板中的 SVG 内容"
__usage__ = """当同时使用 FreeCAD 和 SVG 编辑器（如 Inkscape）时，
在 SVG 编辑器中复制 (Ctrl+C) 一个对象，切换回 FreeCAD 并激活此工具。
这会将剪贴板中的 SVG 内容直接导入到当前活动的 FreeCAD 文档中。"""

import xml.sax
import importSVG
import os
import FreeCAD
import FreeCADGui
from PySide import QtGui
from freecad.Curves import ICONPATH

TOOL_ICON = os.path.join(ICONPATH, 'svg_rv3.svg')


class pasteSVG:
    def Activated(self):
        cb = QtGui.QApplication.clipboard()
        t = cb.text()

        if t[0:5] == '<?xml':
            h = importSVG.svgHandler()
            doc = FreeCAD.ActiveDocument
            if not doc:
                doc = FreeCAD.newDocument("SvgImport")
            h.doc = doc
            xml.sax.parseString(t, h)
            doc.recompute()
            FreeCADGui.SendMsgToActiveView("ViewFit")
        else:
            FreeCAD.Console.PrintError("{} :\n{}\n".format(__title__, __usage__))

    def IsActive(self):
        cb = QtGui.QApplication.clipboard()
        cb_content = cb.text()
        if cb_content[0:5] == '<?xml':
            return True

    def GetResources(self):
        return {'Pixmap': TOOL_ICON,
                'MenuText': __title__,
                'ToolTip': "{}<br><br><b>Usage :</b><br>{}".format(__doc__, "<br>".join(__usage__.splitlines()))}


FreeCADGui.addCommand('pasteSVG', pasteSVG())
