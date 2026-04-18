# SPDX-License-Identifier: LGPL-2.1-or-later

__title__ = ""
__author__ = "Christophe Grellier (Chris_G)"
__license__ = "LGPL 2.1"
__doc__ = """"""

from time import time
from math import pi
from operator import itemgetter

import FreeCAD
import FreeCADGui
import Part
import numpy as np

from .gordon import GordonSurfaceBuilder
from . import _utils
from . import curves_to_surface
from . import TOL3D, TOL2D

CAN_MINIMIZE = True

try:
    from scipy.optimize import minimize
except (ImportError, ValueError):
    CAN_MINIMIZE = False

vec3 = FreeCAD.Vector
vec2 = FreeCAD.Base.Vector2d


class PointOnEdge:
    """定义边上的一个点及其若干阶导数向量
    属性 'continuity' 定义导数向量的阶数
    示例：
    poe = PointOnEdge(我的边, 0.0, 2)
    print(poe.vectors)
    将返回边上参数 0.0 处的点和 2 阶导数
    """
    def __init__(self, edge, parameter=None, continuity=1, size=1.0):
        self._parameter = 0.0
        self._continuity = 1
        self._vectors = []
        self._scale = 1.0
        self._size = size
        self.edge = edge
        if parameter is None:
            self.to_start()
        else:
            self.parameter = parameter
        self.continuity = continuity

    def __repr__(self):
        return "{}(Edge({}),{},{})".format(self.__class__.__name__,
                                           hex(id(self.edge)),
                                           self.parameter,
                                           self.continuity)

    def __str__(self):
        return "{} (Edge({}), {:3.3f}, G{})".format(self.__class__.__name__,
                                                    hex(id(self.edge)),
                                                    self.parameter,
                                                    self.continuity)

    def set_vectors(self):
        res = [self._edge.Curve.getD0(self._parameter),
               self._edge.Curve.getDN(self._parameter, 1)]
        if self._continuity > 1:
            res.extend([self._edge.Curve.getDN(self._parameter, i) for i in range(2, self._continuity + 1)])
        self._vectors = res
        self.size = self._size

    def recompute_vectors(func):
        """重新计算点和导数向量的装饰器"""
        def wrapper(self, arg):
            func(self, arg)
            self.set_vectors()
        return wrapper

    @property
    def parameter(self):
        """定义该点在边上的参数位置"""
        return self._parameter

    @parameter.setter
    @recompute_vectors
    def parameter(self, par):
        if par < self._edge.FirstParameter:
            self._parameter = self._edge.FirstParameter
        elif par > self._edge.LastParameter:
            self._parameter = self._edge.LastParameter
        else:
            self._parameter = par

    @property
    def distance(self):
        """通过距离定义该点在边上的位置"""
        segment = self._edge.Curve.toShape(self._edge.FirstParameter, self._parameter)
        return segment.Length

    @distance.setter
    def distance(self, dist):
        if dist > self._edge.Length:
            self.parameter = self._edge.LastParameter
        elif dist < -self._edge.Length:
            self.parameter = self._edge.FirstParameter
        else:
            self.parameter = self._edge.getParameterByLength(dist)

    @property
    def continuity(self):
        """定义该点的导数向量阶数"""
        return self._continuity

    @continuity.setter
    @recompute_vectors
    def continuity(self, val):
        if val < 0:
            self._continuity = 0
        elif val > 5:
            self._continuity = 5
        else:
            self._continuity = val

    @property
    def edge(self):
        """该点的支撑边"""
        return self._edge

    @edge.setter
    @recompute_vectors
    def edge(self, edge):
        if isinstance(edge, Part.Wire):
            self._edge = edge.approximate(1e-10, 1e-7, 999, 25)
        elif edge.isDerivedFrom("Part::GeomCurve"):
            self._edge = edge.toShape()
        else:
            self._edge = edge

    # 公开向量访问接口
    def __getitem__(self, key):
        if key < len(self._vectors):
            return self._vectors[key] * pow(self._scale, key)

    @property
    def point(self):
        return self._vectors[0]

    @property
    def tangent(self):
        return self._vectors[1] * self._scale

    @property
    def vectors(self):
        return [self._vectors[i] * pow(self._scale, i) for i in range(self.continuity + 1)]
    # ########################

    @property
    def size(self):
        """切向量的长度大小"""
        return self._size

    @size.setter
    def size(self, val):
        """缩放向量，使切向量达到指定长度"""
        if val < 0:
            self._size = min(-1e-7, val)
        else:
            self._size = max(1e-7, val)
        if len(self._vectors) > 1:
            self._scale = val / self._vectors[1].Length

    @property
    def bounds(self):
        return self._edge.ParameterRange

    def to_start(self):
        """移动到边的起点"""
        self.parameter = self._edge.FirstParameter

    def to_end(self):
        """移动到边的终点"""
        self.parameter = self._edge.LastParameter

    def reverse(self):
        """通过反转缩放系数，反向奇数阶导数向量"""
        self.size = -self._size

    def get_tangent_edge(self):
        return Part.makeLine(self.point, self.point + self.tangent)

    def split_edge(self, first=True):
        """在当前参数处切割支撑边，返回一条线"""
        if (self._parameter > self._edge.FirstParameter) and (self._parameter < self._edge.LastParameter):
            return self._edge.split(self._parameter)
        else:
            return Part.Wire([self._edge])

    def first_segment(self):
        if self._parameter > self._edge.FirstParameter:
            return self._edge.Curve.toShape(self._edge.FirstParameter, self._parameter)

    def last_segment(self):
        if self._parameter < self._edge.LastParameter:
            return self._edge.Curve.toShape(self._parameter, self._edge.LastParameter)

    def front_segment(self):
        """返回切向量前方的边段"""
        if self._scale > 0:
            ls = self.last_segment()
            if ls:
                return [self.last_segment()]
        else:
            fs = self.first_segment()
            if fs:
                return [fs.reversed()]
        return []

    def rear_segment(self):
        """返回切向量后方的边段"""
        if self._scale < 0:
            ls = self.last_segment()
            if ls:
                return [self.last_segment()]
        else:
            fs = self.first_segment()
            if fs:
                return [fs.reversed()]
        return []

    def shape(self):
        vecs = [FreeCAD.Vector()] + self.vectors[1:]
        pts = [p + self.point for p in vecs]
        return Part.makePolygon(pts)


class BlendCurve:
    """过渡曲线：生成一条贝塞尔曲线，
    平滑连接两个 PointOnEdge 对象
    """
    def __init__(self, point1, point2):
        self.min_method = 'Nelder-Mead'
        self.min_options = {"maxiter": 2000, "disp": False}
        self.point1 = point1
        self.point2 = point2
        self._curve = Part.BezierCurve()
        self.nb_samples = 32

    def __repr__(self):
        return "{}(Edge1({:3.3f}, G{}), Edge2({:3.3f}, G{}))".format(self.__class__.__name__,
                                                                     self.point1.parameter,
                                                                     self.point1.continuity,
                                                                     self.point2.parameter,
                                                                     self.point2.continuity)

    @staticmethod
    def can_minimize():
        try:
            from scipy.optimize import minimize
            return True
        except ImportError:
            return False

    @property
    def point1(self):
        """定义过渡曲线起点的 PointOnEdge 对象"""
        return self._point1

    @point1.setter
    def point1(self, p):
        self._point1 = p

    @property
    def point2(self):
        """定义过渡曲线终点的 PointOnEdge 对象"""
        return self._point2

    @point2.setter
    def point2(self, p):
        self._point2 = p

    @property
    def scale1(self):
        """第一个点的缩放比例"""
        return self.point1.size / self.chord_length

    @scale1.setter
    def scale1(self, s):
        self.point1.size = s * self.chord_length

    @property
    def scale2(self):
        """第二个点的缩放比例"""
        return self.point2.size / self.chord_length

    @scale2.setter
    def scale2(self, s):
        self.point2.size = s * self.chord_length

    @property
    def scales(self):
        """两个点的缩放比例"""
        return self.scale1, self.scale2

    @scales.setter
    def scales(self, s):
        self.scale1 = s
        self.scale2 = s

    @property
    def chord_length(self):
        return max(1e-6, self.point1.point.distanceToPoint(self.point2.point))

    @property
    def curve(self):
        """返回表示过渡曲线的贝塞尔曲线"""
        return self._curve

    @property
    def shape(self):
        """返回表示过渡曲线的边"""
        return self._curve.toShape()

    def perform(self, vecs=None):
        """生成插值两个点的贝塞尔曲线"""
        if vecs is None:
            self._curve.interpolate([self.point1.vectors, self.point2.vectors])
        else:
            self._curve.interpolate(vecs)
        return self._curve

    def auto_orient(self, tol=1e-3):
        """自动调整两个点的切向量方向
        容差值用于检测平行切向量
        """
        line1 = self.point1.get_tangent_edge()
        line2 = self.point2.get_tangent_edge()
        p1 = line1.Curve.parameter(self.point2.point)
        p2 = line2.Curve.parameter(self.point1.point)
        if p1 < 0:
            self.scale1 = -self.scale1
        if p2 > 0:
            self.scale2 = -self.scale2

    def auto_scale(self, auto_orient=True):
        """自动设置两点缩放比例，与弦长成比例
        可选择先执行自动方向调整
        """
        self.scale1 = 1.0
        self.scale2 = 1.0
        if auto_orient:
            self.auto_orient()

    # 曲线评估方法
    def _curvature_regularity_score(self, scales):
        """返回曲线上最大曲率与最小曲率的差值"""
        self.scale1, self.scale2 = scales
        self.perform()
        curva_list = [self.curve.curvature(p / self.nb_samples) for p in range(self.nb_samples + 1)]
        return (max(curva_list) - min(curva_list))

    def _cp_regularity_score(self, scales):
        """返回连续控制点之间最大距离与最小距离的差值"""
        self.scale1, self.scale2 = scales
        self.perform()
        pts = self.curve.getPoles()
        vecs = []
        for i in range(1, self.curve.NbPoles):
            vecs.append(pts[i] - pts[i - 1])
        poly = Part.makePolygon(pts)
        llist = [v.Length for v in vecs]
        return poly.Length + (max(llist) - min(llist))

    def _total_cp_angular(self, scales):
        """返回连续控制点之间最大角度与最小角度的差值"""
        self.scale1, self.scale2 = scales
        self.perform()
        poly = Part.makePolygon(self.curve.getPoles())
        angles = []
        for i in range(1, len(poly.Edges)):
            angles.append(poly.Edges[i - 1].Curve.Direction.getAngle(poly.Edges[i].Curve.Direction))
        return (max(angles) - min(angles))

    def set_regular_poles(self):
        """迭代优化：使控制点间距均匀规则"""
        self.scales = 1.0
        self.auto_orient()
        minimize(self._cp_regularity_score,
                 [self.scale1, self.scale2],
                 method=self.min_method,
                 options=self.min_options)

    def minimize_curvature(self):
        """迭代优化：最小化曲线曲率波动"""
        self.scales = 1.0
        self.auto_orient()
        minimize(self._curvature_regularity_score,
                 [self.scale1, self.scale2],
                 method=self.min_method,
                 options=self.min_options)

    def minimize_angular_variation(self):
        """迭代优化：最小化控制点方向角变化"""
        self.scales = 1.0
        self.auto_orient()
        minimize(self._total_cp_angular,
                 [self.scale1, self.scale2],
                 method=self.min_method,
                 options=self.min_options)


class ValueOnEdge:
    """沿边插值浮点数值
    voe = ValueOnEdge(一条边, 值=None)
    """
    def __init__(self, edge, value=None):
        self._edge = edge
        self._curve = Part.BSplineCurve()
        self._pts = []
        self._closed = edge.isClosed()
        self._first_param_picked = False
        self._last_param_picked = False
        if value is not None:
            self.set(value)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.values)

    @property
    def values(self):
        return [v.y for v in self._pts]

    def set(self, val):
        """设置常量值或一组均匀分布的数值列表"""
        self._pts = []
        if isinstance(val, (list, tuple)):
            if len(val) == 1:
                val *= 2
            params = np.linspace(self._edge.FirstParameter, self._edge.LastParameter, len(val))
            for i in range(len(val)):
                self.add(val[i], abs_par=params[i], recompute=False)
        elif isinstance(val, (int, float)):
            self.set([val, val])
        self._compute()

    def _get_real_param(self, abs_par=None, rel_par=None, dist_par=None, point=None):
        """检查范围，从以下参数返回真实边参数：
        - 绝对参数
        - 归一化参数 [0.0, 1.0]
        - 距离（正=起点，负=终点）
        """
        if abs_par is not None:
            return abs_par
        elif rel_par is not None:
            return self._edge.FirstParameter + rel_par * (self._edge.LastParameter - self._edge.FirstParameter)
        elif dist_par is not None:
            return self._edge.getParameterByLength(dist_par)
        elif point is not None:
            p = self._edge.Curve.parameter(point)
            if self._closed:
                is_first = abs(p - self._edge.Curve.FirstParameter) < TOL3D
                is_last = abs(p - self._edge.Curve.LastParameter) < TOL3D
                if is_first:
                    if self._first_param_picked:
                        p = self._edge.Curve.LastParameter
                        self._last_param_picked = True
                    else:
                        self._first_param_picked = True
                if is_last:
                    if self._last_param_picked:
                        p = self._edge.Curve.FirstParameter
                        self._first_param_picked = True
                    else:
                        self._last_param_picked = True
                if self._first_param_picked and self._last_param_picked:
                    self._first_param_picked = False
                    self._last_param_picked = False
            return p
        else:
            raise ValueError("未提供参数")

    def add(self, val, abs_par=None, rel_par=None, dist_par=None, point=None, recompute=True):
        """在指定参数处为边添加一个数值
        输入：
        - val：浮点数值
        - abs_par：绝对参数
        - rel_par：归一化参数
        - dist_par：距离
        - recompute：是否立即重新计算插值曲线
        """
        par = self._get_real_param(abs_par, rel_par, dist_par, point)
        self._pts.append(FreeCAD.Vector(par, val, 0.0))
        self._pts = sorted(self._pts, key=itemgetter(0))
        if recompute:
            self._compute()

    def reset(self):
        self._pts = []

    def _compute(self):
        if len(self._pts) < 2:
            return
        par = [p.x for p in self._pts]
        if self._edge.isClosed() and self._edge.Curve.isPeriodic() and len(self._pts) > 2:
            self._curve.interpolate(Points=self._pts[:-1], Parameters=par, PeriodicFlag=True)
        else:
            self._curve.interpolate(Points=self._pts, Parameters=par, PeriodicFlag=False)

    def value(self, abs_par=None, rel_par=None, dist_par=None):
        """返回指定参数处的插值数值"""
        if len(self._pts) == 1:
            return self._pts[0].y
        par = self._get_real_param(abs_par, rel_par, dist_par)
        return self._curve.value(par).y


def add2d(p1, p2):
    return vec2(p1.x + p2.x, p1.y + p2.y)


def mul2d(vec, fac):
    return vec2(vec.x * fac, vec.y * fac)


def curve2d_extend(curve, start=0.5, end=0.5):
    """通过线性切线延伸二维几何曲线的两端
    start 和 end 是曲线长度的比例系数
    返回 B 样条曲线
    """
    bs = curve.toBSpline(curve.FirstParameter, curve.LastParameter)
    t1 = mul2d(bs.tangent(bs.FirstParameter), -1.0)
    t2 = bs.tangent(bs.LastParameter)
    poles = bs.getPoles()
    mults = bs.getMultiplicities()
    knots = bs.getKnots()

    pre = list()
    post = list()
    for i in range(bs.Degree):
        le = bs.length() * (bs.Degree - i) / bs.Degree
        pre.append(add2d(bs.value(bs.FirstParameter), mul2d(t1, start * le)))
        post.append(add2d(bs.value(bs.LastParameter), mul2d(t2, end * le)))
    newpoles = pre + poles + post

    mults.insert(1, bs.Degree)
    mults.insert(len(mults) - 2, bs.Degree)
    prange = bs.LastParameter - bs.FirstParameter
    knots.insert(0, bs.FirstParameter - prange * start)
    knots.append(bs.LastParameter + prange * end)
    try:
        bs.buildFromPolesMultsKnots(newpoles, mults, knots, bs.isPeriodic(), bs.Degree)
    except Part.OCCError:
        print(bs.Degree)
        print(len(newpoles))
        print(sum(mults))
        print(len(knots))
    return bs


def intersection2d(curve, c1, c2):
    inter11 = curve.intersectCC(c1)
    inter12 = curve.intersectCC(c2)
    if len(inter11) > 0 and len(inter12) > 0:
        return (curve, inter11[0], inter12[0])
    else:
        return False


def get_offset_curve(bc, c1, c2, dist=0.1):
    """计算距离 bc 曲线 dist 的二维偏移曲线，要求与 c1、c2 相交
    返回偏移曲线和交点
    """
    off1 = Part.Geom2d.OffsetCurve2d(bc, dist)
    intersec = intersection2d(off1, c1, c2)
    if intersec:
        return intersec

    off2 = Part.Geom2d.OffsetCurve2d(bc, -dist)
    intersec = intersection2d(off1, c1, c2)
    if intersec:
        return intersec

    ext1 = curve2d_extend(off1, 0.2, 0.2)
    intersec = intersection2d(ext1, c1, c2)
    if intersec:
        return intersec

    ext2 = curve2d_extend(off2, 0.2, 0.2)
    intersec = intersection2d(ext2, c1, c2)
    if intersec:
        return intersec


class EdgeOnFace:
    """定义位于面上的一条边
    提供导数数据，用于从该边创建光滑曲面
    属性 'continuity' 定义导数向量阶数
    """
    def __init__(self, edge, face, continuity=1):
        self._face = face
        self._edge = edge
        self._offset = None
        self._angle = ValueOnEdge(edge, 90.0)
        self._size = ValueOnEdge(edge, 1.0)
        self.continuity = continuity

    def __repr__(self):
        return "{} (Edge {}, Face {}, G{})".format(self.__class__.__name__,
                                                   hex(id(self._edge)),
                                                   hex(id(self._face)),
                                                   self.continuity)

    def _get_real_param(self, abs_par=None, rel_par=None, dist_par=None):
        """检查范围，返回真实边参数"""
        if abs_par is not None:
            return abs_par
        elif rel_par is not None:
            return self._edge.FirstParameter + rel_par * (self._edge.LastParameter - self._edge.FirstParameter)
        elif dist_par is not None:
            return self._edge.getParameterByLength(dist_par)
        else:
            raise ValueError("未提供参数")

    def _relative_param(self, par):
        """返回给定真实参数对应的归一化参数"""
        return (par - self._edge.FirstParameter) / (self._edge.LastParameter - self._edge.FirstParameter)

    @property
    def continuity(self):
        """定义该面边的导数向量阶数"""
        return self._continuity

    @continuity.setter
    def continuity(self, val):
        if val < 0:
            self._continuity = 0
        elif val > 5:
            self._continuity = 5
        else:
            self._continuity = val

    @property
    def angle(self):
        """返回定义沿边角度的对象"""
        return self._angle

    @angle.setter
    def angle(self, angle):
        self._angle.set(angle)

    @property
    def size(self):
        """返回定义沿边大小的对象"""
        return self._size

    @size.setter
    def size(self, size):
        self._size.set(size)

    def get_offset_curve2d(self, dist=0.1):
        cos = list()
        idx = -1
        nbe = len(self._face.OuterWire.OrderedEdges)
        for n, e in enumerate(self._face.OuterWire.OrderedEdges):
            c = self._face.curveOnSurface(e)
            if len(c) == 3:
                cos.append(c[0].toBSpline(c[1], c[2]))
            else:
                FreeCAD.Console.PrintError("提取二维几何失败")
            if e.isPartner(self._edge):
                idx = n

        # 获取相邻曲线索引
        id1 = idx - 1 if idx > 0 else nbe - 1
        id2 = idx + 1 if idx < nbe - 1 else 0

        # 获取偏移曲线
        off = get_offset_curve(cos[idx], cos[id1], cos[id2], dist)
        if off:
            p1 = off[0].parameter(off[1])
            p2 = off[0].parameter(off[2])
            if p1 < p2:
                return off[0].toBSpline(p1, p2)
            else:
                return off[0].toBSpline(p2, p1)

        off = Part.Geom2d.OffsetCurve2d(cos[idx], dist)
        pt = off.value(0.5 * (off.FirstParameter + off.LastParameter))
        if self._face.isPartOfDomain(pt.x, pt.y):
            return off.toBSpline(off.FirstParameter, off.LastParameter)
        else:
            off = Part.Geom2d.OffsetCurve2d(cos[idx], -dist)
            return off.toBSpline(off.FirstParameter, off.LastParameter)

    def curve_on_surface(self):
        cos = self._face.curveOnSurface(self._edge)
        if cos is None:
            proj = self._face.project([self._edge])
            cos = self._face.curveOnSurface(proj.Edge1)
        return cos

    def cross_curve(self, abs_par=None, rel_par=None, dist_par=None):
        par = self._get_real_param(abs_par, rel_par, dist_par)
        if self._offset is None:
            self._offset = self.get_offset_curve2d()
        cos, fp, lp = self.curve_on_surface()
        off_par = self._offset.FirstParameter + self._relative_param(par) * (self._offset.LastParameter - self._offset.FirstParameter)
        line = Part.Geom2d.Line2dSegment(self._offset.value(off_par), cos.value(par))
        line3d = line.toShape(self._face.Surface)
        return line3d

    def valueAtPoint(self, pt):
        """返回给定点处的 PointOnEdge 对象"""
        if isinstance(pt, FreeCAD.Vector):
            par = self._edge.Curve.parameter(pt)
            if par < self._edge.FirstParameter and self._edge.Curve.isClosed():
                if self._edge.Curve.isPeriodic():
                    pass
                else:
                    par += self._edge.LastParameter - self._edge.FirstParameter
            return self.value(abs_par=par)

    def value(self, abs_par=None, rel_par=None, dist_par=None):
        """返回指定参数处的 PointOnEdge 对象"""
        par = self._get_real_param(abs_par, rel_par, dist_par)
        cc = self.cross_curve(abs_par=par)
        d, pts, info = cc.distToShape(self._edge)
        new_par = cc.Curve.parameter(pts[0][0])
        size = self.size.value(abs_par=par)
        if cc:
            poe = PointOnEdge(cc, new_par, self.continuity, size)
            return poe

    def discretize(self, num=10):
        """返回沿边均匀分布的 num 个 PointOnEdge 对象列表"""
        poe = []
        for i in np.linspace(0.0, 1.0, num):
            poe.append(self.value(rel_par=i))
        return poe

    def shape(self, num=10):
        """返回沿边 num 个 PointOnEdge 对象的组合体"""
        return Part.Compound([poe.rear_segment() for poe in self.discretize(num)])


class BlendSurface:
    """B 样条曲面：平滑连接两个 EdgeOnFace 对象"""
    def __init__(self, edge1, face1, edge2, face2):
        self.edge1 = EdgeOnFace(edge1, face1)
        self.edge2 = EdgeOnFace(edge2, face2)
        self._ruled_surface = None
        self._surface = None
        self._curves = []

    def __repr__(self):
        return "{}(Edge1({}, G{}), Edge2({}, G{}))".format(self.__class__.__name__,
                                                           hex(id(self.edge1)),
                                                           self.edge1.continuity,
                                                           hex(id(self.edge2)),
                                                           self.edge2.continuity)

    @property
    def continuity(self):
        """返回过渡曲面的连续性"""
        return [self.edge1.continuity, self.edge2.continuity]

    @continuity.setter
    def continuity(self, args):
        if isinstance(args, (int, float)):
            self.edge1.continuity = args
            self.edge2.continuity = args
        elif isinstance(args, (list, tuple)):
            self.edge1.continuity = args[0]
            self.edge2.continuity = args[1]

    @property
    def curves(self):
        """返回构成过渡曲面的过渡曲线"""
        return self._curves

    @property
    def edges(self):
        """返回过渡曲线的边组合体"""
        el = [c.toShape() for c in self._curves]
        return Part.Compound(el)

    @property
    def surface(self):
        """返回表示过渡曲面的 B 样条曲面"""
        guides = [bezier.toBSpline() for bezier in self._curves]
        cts = curves_to_surface.CurvesToSurface(guides)
        cts.Parameters = self._params
        s1 = cts.interpolate()
        s2 = curves_to_surface.ruled_surface(self.rails[0].toShape(), self.rails[1].toShape(), True).Surface
        s2.exchangeUV()
        s3 = curves_to_surface.U_linear_surface(s1)
        gordon = curves_to_surface.Gordon(s1, s2, s3)
        self._surface = gordon.Surface
        return self._surface

    @property
    def face(self):
        """返回表示过渡曲面的面"""
        return self.surface.toShape()

    @property
    def rails(self):
        u0, u1, v0, v1 = self.ruled_surface.bounds()
        return self.ruled_surface.vIso(v0), self.ruled_surface.vIso(v1)

    @property
    def ruled_surface(self):
        if self._ruled_surface is None:
            self._ruled_surface = curves_to_surface.ruled_surface(self.edge1._edge, self.edge2._edge, True).Surface
        return self._ruled_surface

    def sample(self, num=3):
        ruled = self.ruled_surface
        u0, u1, v0, v1 = ruled.bounds()
        e1, e2 = self.rails
        if isinstance(num, int):
            params = np.linspace(u0, u1, num)
        return params

    def blendcurve_at(self, par):
        e1, e2 = self.rails
        return BlendCurve(self.edge1.valueAtPoint(e1.value(par)), self.edge2.valueAtPoint(e2.value(par)))

    def minimize_curvature(self, arg=3):
        self.edge1.size.reset()
        self.edge2.size.reset()
        e1, e2 = self.rails
        for p in self.sample(arg):
            bc = self.blendcurve_at(p)
            bc.minimize_curvature()
            self.edge1.size.add(val=bc.point1.size, point=e1.value(p))
            self.edge2.size.add(val=bc.point2.size, point=e2.value(p))

    def auto_scale(self, arg=3):
        self.edge1.size.reset()
        self.edge2.size.reset()
        e1, e2 = self.rails
        for p in self.sample(arg):
            bc = self.blendcurve_at(p)
            bc.auto_scale()
            self.edge1.size.add(val=bc.point1.size, point=e1.value(p))
            self.edge2.size.add(val=bc.point2.size, point=e2.value(p))

    def perform(self, arg=20):
        bc_list = []
        for p in self.sample(arg):
            bc = self.blendcurve_at(p)
            bc_list.append(bc.perform())
        self._curves = bc_list
        self._params = self.sample(arg)


def test_blend_surface():
    doc1 = FreeCAD.ActiveDocument
    o1 = doc1.getObject('Ruled_Surface001')
    e1 = o1.Shape.Edge1
    f1 = o1.Shape.Face1
    o2 = doc1.getObject('Ruled_Surface')
    e2 = o2.Shape.Edge3
    f2 = o2.Shape.Face1

    from freecad.Curves import blend_curve as bc

    num = 21

    bs = bc.BlendSurface(e1, f1, e2, f2)
    bs.continuity = 3
    bs.minimize_curvature()
    bs.perform(num)
    Part.show(bs.edges)
    bsface = bs.face
    Part.show(bsface)
    shell = Part.Shell([f1, bsface, f2])
    print("有效壳层 : {}".format(shell.isValid()))
    shell.check(True)


def main():
    """主函数：选择两条边创建平滑过渡曲线"""
    sel = FreeCADGui.Selection.getSelectionEx()
    edges = []
    pp = []
    for s in sel:
        edges.extend(s.SubObjects)
        pp.extend(s.PickedPoints)

    e0 = edges[0]
    p0 = e0.Curve.parameter(pp[0])
    e1 = edges[1]
    p1 = e1.Curve.parameter(pp[1])

    start = time()
    poe1 = PointOnEdge(e0, p0, 3)
    poe2 = PointOnEdge(e1, p1, 3)
    poe1.size = 0.1
    poe2.size = 0.1
    fillet = BlendCurve(poe1, poe2)
    fillet.nb_samples = 200
    fillet.auto_orient()
    fillet.minimize_curvature()
    fillet.perform()
    print("优化耗时 = {}s".format(time() - start))
    print("最终缩放长度 = {} - {}".format(poe1.tangent.Length, poe2.tangent.Length))
    Part.show(fillet.curve.toShape())
    return fillet


if __name__ == '__main__':
    main()