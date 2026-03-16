import Part
from freecad.Curves.lib.logger import FCLogger

logger = FCLogger("Debug", "lib/face_builder")


def face_validate(face):
    "Tries to fix a non-valid face"
    if face.isValid():
        return face
    face.validate()
    if face.isValid():
        logger.debug("face validate success.")
    else:
        logger.debug("face validate failed.")
    return face


def shapefix_builder(surface, wires=[], tol=1e-7):
    """
    Create a face with surface and wires
    It uses Part.Shapefix.Face tool.
    new_face = shapefix_builder(face, surface=[], tol=1e-7)
    """
    ffix = Part.ShapeFix.Face(surface, tol)
    for w in wires:
        ffix.add(w)
    ffix.perform()
    if ffix.fixOrientation():
        logger.debug("fixed Orientation")
    if ffix.fixMissingSeam():
        logger.debug("fixed Missing Seam")
    return face_validate(ffix.face())


def change_surface(surface, face, tol=1e-7):
    """
    Create a face with a new surface support
    new_face = change_surface(surface, face, tol=1e-7)
    """
    return shapefix_builder(surface, face.Wires, tol)



