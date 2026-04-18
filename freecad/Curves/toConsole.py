# SPDX-License-Identifier: LGPL-2.1-or-later

__title__ = '对象导出到控制台'
__author__ = 'Christophe Grellier (Chris_G)'
__license__ = 'LGPL 2.1'
__doc__ = '在 Python 控制台中直接访问所选对象。'
__usage__ = """在树状视图 (TreeView) 或 3D 视图中选择若干对象，然后激活工具。
系统将在 Python 控制台中创建相应的变量，以便您通过代码访问这些选定对象。"""

import FreeCAD
import FreeCADGui
import os
from freecad.Curves import _utils
from freecad.Curves import ICONPATH

TOOL_ICON = os.path.join(ICONPATH, 'toconsole.svg')
# debug = _utils.debug
debug = _utils.doNothing


class ToConsole:
    "Brings the selected objects to the python console"
    def GetResources(self):
        return {'Pixmap': TOOL_ICON,
                'MenuText': __title__,
                'Accel': "",
                'ToolTip': "{}<br><br><b>Usage :</b><br>{}".format(__doc__, "<br>".join(__usage__.splitlines()))}

    def Activated(self):
        doc = ''
        obj = ''
        sublinks = '('

        doc_num = 0
        obj_num = 0
        face_num = 0
        edge_num = 0
        vert_num = 0

        selection = FreeCADGui.Selection.getSelectionEx()
        if selection == []:
            FreeCAD.Console.PrintError('Selection is empty.\n')

        for selobj in selection:
            if not selobj.DocumentName == doc:
                doc = selobj.DocumentName
                doc_num += 1
                FreeCADGui.doCommand("doc{} = FreeCAD.getDocument('{}')".format(doc_num, doc))
            if not selobj.ObjectName == obj:
                obj = selobj.ObjectName
                obj_num += 1
                FreeCADGui.doCommand("o{} = doc{}.getObject('{}')".format(obj_num, doc_num, obj))
            if selobj.HasSubObjects:
                for sub in selobj.SubElementNames:
                    sublinks += "(o{},('{}')),".format(obj_num, sub)
                    if 'Vertex' in sub:
                        vert_num += 1
                        FreeCADGui.doCommand("v{} = o{}.Shape.{}".format(vert_num, obj_num, sub))
                    if 'Edge' in sub:
                        edge_num += 1
                        FreeCADGui.doCommand("e{} = o{}.Shape.{}".format(edge_num, obj_num, sub))
                    if 'Face' in sub:
                        face_num += 1
                        FreeCADGui.doCommand("f{} = o{}.Shape.{}".format(face_num, obj_num, sub))
        sublinks += ")"
        if len(sublinks) > 1:
            FreeCADGui.doCommand("_sub_link_buffer = {}".format(sublinks))
        if obj_num > 1:
            ol = ''
            for oi in range(obj_num):
                ol += "o{},".format(oi + 1)
            FreeCADGui.doCommand("ol = ({})".format(ol))
        if vert_num > 1:
            vl = ''
            for vi in range(vert_num):
                vl += "v{},".format(vi + 1)
            FreeCADGui.doCommand("vl = ({})".format(vl))
        if edge_num > 1:
            el = ''
            for ei in range(edge_num):
                el += "e{},".format(ei + 1)
            FreeCADGui.doCommand("el = ({})".format(el))
        if face_num > 1:
            fl = ''
            for fi in range(face_num):
                fl += "f{},".format(fi + 1)
            FreeCADGui.doCommand("fl = ({})".format(fl))

    def IsActive(self):
        if FreeCAD.ActiveDocument:
            return True
        else:
            return False


FreeCADGui.addCommand('to_console', ToConsole())
