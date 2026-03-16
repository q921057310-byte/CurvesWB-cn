import FreeCAD
import Part


def mean_vector(vectors):
    "Return the mean vector of a list of vectors"
    point = FreeCAD.Vector()
    for pt in vectors:
        point += pt
    point /= len(vectors)
    return point


def mean_line(lines):
    "Return the mean line of a list of lines"
    direction = mean_vector([li.Direction for li in lines])
    location = mean_vector([li.Location for li in lines])
    return Part.Line(location, location + direction)


def lines_intersection(lines, tol=1e-7, size=1e6):
    """
    If lines all intersect into one point.
    Returns this point, or None otherwise.
    Input :
    lines : list of Part.Line
    tol (float): search tolerance
    size (float): size for edge conversion
    Return :
    Converging point (FreeCAD.Vector) or None
    """
    interlist = []
    for i in range(len(lines) - 1):
        li1 = lines[i].toShape(-size, size)
        li2 = lines[i + 1].toShape(-size, size)
        d, pts, info = li1.distToShape(li2)
        # Part.show(Part.Compound([li1, li2]))
        if d > tol:
            # print(f"Find_apex 1, intersection #{i} : {d} out of tolerance {tol}")
            # Part.show(Part.Compound([li1, li2]))
            return None
        interlist.append(0.5 * pts[0][0] + 0.5 * pts[0][1])
    for i in range(len(interlist) - 1):
        d = interlist[i].distanceToPoint(interlist[i + 1])
        if d > tol:
            # print(f"Find_apex 2, intersection #{i} : {d} out of tolerance {tol}")
            return None
    return mean_vector(interlist)


def planes_intersection(planes, tol=1e-7):
    """
    If planes all intersect into one line, return this line.
    If planes intersect into parallel lines, return the direction.
    Else, return None
    Input :
    planes : list of Part.Plane
    tol (float): search tolerance
    Return :
    Intersection line (Part.Line)
    or intersection direction (FreeCAD.Vector)
    or None
    """
    center = None
    interlist = []
    for i in range(len(planes) - 1):
        inter = planes[i].intersect(planes[i + 1])
        interlist.extend(inter)
    if len(interlist) == 0:
        # All planes are parallel
        return None
    # Part.show(Part.Compound([il.toShape(-100, 100) for il in interlist]))
    coincident = True
    for i in range(len(interlist) - 1):
        i1 = interlist[i]
        i2 = interlist[i + 1]
        dotprod = i1.Direction.dot(i2.Direction)
        if (1.0 - abs(dotprod)) > tol:
            # print(f"plane intersection #{i}: out of tolerance {tol}")
            return None
        if dotprod < 0:
            i2.reverse()
        if i1.Location.distanceToLine(i2.Location, i2.Direction) > tol:
            coincident = False
    axis = mean_vector([li.Direction for li in interlist])
    # print(f"Found Axis {axis}")
    if coincident:
        center = mean_vector([li.Location for li in interlist])
        # print(f"Found Center {center}")
        return Part.Line(center, center + axis)
    return axis

