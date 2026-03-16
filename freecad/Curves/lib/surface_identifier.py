import FreeCAD
import Part
# from random import random
from math import pi
from freecad.Curves.lib.trimmed_surface import TrimmedSurface
from freecad.Curves.lib import face_builder
from freecad.Curves.lib.logger import FCLogger
from freecad.Curves.lib.geometry import lines_intersection, planes_intersection


class SurfaceIdentifier:
    "Tries to identify canonical surface of a face"

    def __init__(self, face, num_samples=10, tol=1e-7):
        self.face = face
        self.num_samples = num_samples
        self.bounds = self.face.ParameterRange
        self.tol = tol
        self.Axis = None
        self.Apex = None
        self.SemiAngle = None
        self.Center = None
        self.Radius = None
        self.logger = FCLogger("Debug", "SurfaceIdentifier")

    def is_canonical(self):
        types = ('Part::GeomPlane',
                 'Part::GeomCylinder',
                 'Part::GeomCone',
                 'Part::GeomSphere'
                 'Part::GeomToroid')
        if self.face.Surface.TypeId in types:
            return True
        return False

    def uniform_UV(self):
        "Uniform generator of (u, v) parameters in the source face bounds"
        u0, u1, v0, v1 = self.bounds
        urange = u1 - u0
        vrange = v1 - v0
        for i in range(self.num_samples):
            u = u0 + i * urange / (self.num_samples - 1)
            v = v0 + i * vrange / (self.num_samples - 1)
            yield u, v

    # def random_UV(self):
    #     "Random generator of (u, v) parameters in the source face bounds"
    #     i = 0
    #     u0, u1, v0, v1 = self.bounds
    #     urange = u1 - u0
    #     vrange = v1 - v0
    #     while i < self.num_samples:
    #         u = u0 + random() * urange
    #         v = v0 + random() * vrange
    #         i += 1
    #         yield u, v

    def sample_lines(self):
        "Return a list of lines along minimal curvature of source face"
        lines = []
        for u, v in self.uniform_UV():
            lines.append(self.min_curva_line(u, v))
        return lines

    def sample_planes(self):
        "Return a list of planes normal to maximal curvature of source face"
        planes = []
        for u, v in self.uniform_UV():
            planes.append(self.max_curva_plane(u, v))
        return planes

    def surface_point(self, u, v):
        return self.face.valueAt(u, v)

    def curva_dir(self, u, v):
        "Return maximal and minimal curvature directions at (u,v)"
        macudi, micudi = self.face.Surface.curvatureDirections(u, v)
        macu = abs(self.face.Surface.curvature(u, v, "Max"))
        micu = abs(self.face.Surface.curvature(u, v, "Min"))
        if (macudi.Length < self.tol) or (micudi.Length < self.tol):
            self.logger.info(f"Curvature Directions Error: ({macudi}, {micudi})")
        if macu < micu:
            return micudi, macudi
        return macudi, micudi

    def min_curva_line(self, u, v):
        "Return a line along minimal curvature at (u,v)"
        pt = self.surface_point(u, v)
        di = self.curva_dir(u, v)[1]
        # print(pt, di)
        return Part.Line(pt, pt + di)

    def max_curva_line(self, u, v):
        "Return a line along maximal curvature at (u,v)"
        pt = self.surface_point(u, v)
        di = self.curva_dir(u, v)[0]
        return Part.Line(pt, pt + di)

    def min_curva_plane(self, u, v):
        "Return a plane normal to minimal curvature at (u,v)"
        pt = self.surface_point(u, v)
        di = self.curva_dir(u, v)[1]
        return Part.Plane(pt, di)

    def max_curva_plane(self, u, v):
        "Return a plane normal to maximal curvature at (u,v)"
        pt = self.surface_point(u, v)
        di = self.curva_dir(u, v)[0]
        return Part.Plane(pt, di)

    def fix_axis_orientation(self, axis):
        pt1 = self.face.valueAt(self.bounds[0], self.bounds[2])
        pt2 = self.face.valueAt(self.bounds[1], self.bounds[3])
        proj1 = axis.projectPoint(pt1)
        proj2 = axis.projectPoint(pt2)
        par1 = axis.parameter(proj1)
        par2 = axis.parameter(proj2)
        if par2 < par1:
            return Part.Line(proj2, proj2 - axis.Direction)
        return Part.Line(proj1, proj1 + axis.Direction)

    def cone_data(self, apex, axis):
        "Compute semi-angle, center and radius of a cone"
        axis_line = Part.Line(apex, apex + axis.Direction)
        pt1 = self.face.valueAt(self.bounds[0], self.bounds[2])
        pt2 = self.face.valueAt(self.bounds[1], self.bounds[3])
        proj1 = axis_line.projectPoint(pt1)
        proj2 = axis_line.projectPoint(pt2)
        par1 = axis_line.parameter(proj1)
        par2 = axis_line.parameter(proj2)
        # print(par1, par2)
        radius1 = pt1.distanceToPoint(proj1)
        radius2 = pt2.distanceToPoint(proj2)
        line1 = FreeCAD.Vector(0, par2 - par1, 0)
        line2 = FreeCAD.Vector(radius2, par2, 0) - FreeCAD.Vector(radius1, par1, 0)
        angle = line1.getAngle(line2)
        if par2 < par1:
            angle = -angle
        return angle, proj1, radius1

    def basis_curve(self):
        "Returns the basis curve of a surface of extrusion"
        u0, u1, v0, v1 = self.bounds
        pt = self.face.valueAt(0.5 * (u0 + u1), 0.5 * (v0 + v1))
        plane = Part.Plane(pt, self.Direction)
        intersect = plane.intersectSS(self.face.Surface)
        return intersect

    # Get canonical surfaces

    def get_sphere(self):
        lines = []
        for u, v in self.uniform_UV():
            p1 = self.face.valueAt(u, v)
            n = self.face.normalAt(u, v)
            li = Part.Line(p1, p1 + n)
            lines.append(li)
        center = lines_intersection(lines)
        if center is None:
            return
        pt = self.face.valueAt(self.bounds[0], self.bounds[2])
        radius = pt.distanceToPoint(center)
        sph = Part.Sphere()
        sph.Center = center
        sph.Radius = radius
        return sph

    def get_plane(self):
        if self.face.findPlane(self.tol):
            u0, u1, v0, v1 = self.bounds
            p1 = self.face.valueAt(u0, v0)
            p2 = self.face.valueAt(u1, v0)
            p3 = self.face.valueAt(u0, v1)
            return Part.Plane(p1, p2, p3)

    def get_cylinder(self, axis):
        cyl = Part.Cylinder()
        cyl.Axis = axis.Direction
        cyl.Center = axis.Location
        pt = self.face.valueAt(self.bounds[0], self.bounds[2])
        cyl.Radius = pt.distanceToLine(axis.Location, axis.Direction)
        return cyl

    def get_cone(self, apex, axis):
        cone = Part.Cone()
        cone.Axis = axis.Direction
        semiangle, center, radius = self.cone_data(apex, axis)
        cone.Center = center
        cone.Radius = radius
        cone.SemiAngle = -semiangle
        return cone

    def get_extrusion_surf(self, axis):
        cog = self.face.CenterOfGravity
        pl = Part.Plane(cog, axis)
        curve = self.face.Surface.intersectSS(pl)[0]
        ext = Part.SurfaceOfExtrusion(curve, axis)
        return ext

    def fix_rotation(self, surf):
        u0, u1, v0, v1 = self.bounds
        pt1 = self.face.valueAt(0.5 * (u0 + u1), 0.5 * (v0 + v1))
        axis_line = Part.Line(surf.Center, surf.Center + surf.Axis)
        pt2 = axis_line.projectPoint(pt1)
        iso = surf.uIso(surf.bounds()[0])
        pl = Part.Plane(pt2, surf.Axis)
        pt = pl.intersect(iso)[0][0]
        pt3 = pt.toShape().Point
        v1 = pt2 - pt1
        v2 = pt3 - pt2
        angle = v2.getAngle(v1) * 180 / pi
        cross = v2.cross(v1)
        dot = cross.dot(surf.Axis)
        if dot < 0:
            angle = -angle
        self.logger.debug(f"Rotating {angle:.2f}°")
        plm = FreeCAD.Placement()
        plm.rotate(surf.Center, surf.Axis, angle)
        surf.transform(plm.Matrix)
        return surf

    def get_surface(self):
        "Search and return canonical surface"
        if self.is_canonical():
            return None
        pl = self.get_plane()
        if pl:
            self.logger.info("Surface is a plane")
            return pl
        sph = self.get_sphere()
        if sph:
            self.logger.info("Surface is a sphere")
            return sph
        axis = planes_intersection(self.sample_planes(), self.tol)
        apex = lines_intersection(self.sample_lines(), self.tol)
        self.logger.info("Apex : ", apex)
        if isinstance(axis, Part.Line):
            axis = self.fix_axis_orientation(axis)
            if apex:
                self.logger.info("Surface is a cone")
                cone = self.get_cone(apex, axis)
                return self.fix_rotation(cone)
            self.logger.info("Surface is a cylinder")
            cyl = self.get_cylinder(axis)
            return self.fix_rotation(cyl)
        elif axis:
            self.logger.info("Surface is an extrusion")
            extr = self.get_extrusion_surf(axis)
            return extr
        else:
            self.logger.info("Surface is not canonical")
        return None


# *** Test Script ***

import FreeCADGui
from freecad.Curves.lib.trimmed_surface import TrimmedSurface

log = FCLogger("Debug")

sel = FreeCADGui.Selection.getSelection()
for o in sel:
    log.debug(f"--- {o.Label} analysis\n")
    faces = []
    for i, face in enumerate(o.Shape.Faces):
        log.debug(f"Face{i + 1} ({face.Surface.TypeId})")
        sr = SurfaceIdentifier(face, 10, 1e-7)
        # if sr.is_canonical():
        #     faces.append(face)
        #     continue
        # sr.bounds = face.ParameterRange
        surf = sr.get_surface()
        if surf:
            nf = face_builder.change_surface(surf, face)
            # Part.show(nf, f"Face{i + 1}")
            if isinstance(nf, Part.Face):
                faces.append(nf)
        else:
            faces.append(face)
    shell = Part.Shell(faces)
    shell.sewShape()
    solid = Part.Solid(shell)
    Part.show(solid, f"{o.Label}_Canonical")

        # for pl in sr.sample_planes():
        #     rts = Part.RectangularTrimmedSurface(pl, -100, 100, -100, 100)
        #     Part.show(rts.toShape())

"""
from importlib import reload
from freecad.Curves.lib import surface_identifier
reload(surface_identifier)
"""




