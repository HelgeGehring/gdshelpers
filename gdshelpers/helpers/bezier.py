import numpy as np


class CubicBezierCurve(object):
    def __init__(self, p0, p1, p2, p3):
        self._p0, self._p1, self._p2, self._p3 = [np.asarray(p) for p in (p0, p1, p2, p3)]

    def evaluate(self, t):
        return (1 - t) ** 3 * self._p0[..., None] + 3 * (1 - t) ** 2 * t * self._p1[..., None] \
               + 3 * (1 - t) * t ** 2 * self._p2[..., None] + t ** 3 * self._p3[..., None]

    def evaluate_d1(self, t):
        return 3 * (1 - t) ** 2 * (self._p1[..., None] - self._p0[..., None]) \
               + 6 * (1 - t) * t * (self._p2[..., None] - self._p1[..., None]) \
               + 3 * t ** 2 * (self._p3[..., None] - self._p2[..., None])

    def split(self, t):
        """
        Split the cubic Bezier curve into two new cubic Bezier, both describing one part of the curve.

        :param t:
        :return:
        """
        p1, p2, p3, p4 = self._p0, self._p1, self._p2, self._p3

        p12 = (p2 - p1) * t + p1
        p23 = (p3 - p2) * t + p2
        p34 = (p4 - p3) * t + p3

        p123 = (p23 - p12) * t + p12
        p234 = (p34 - p23) * t + p23

        p1234 = (p234 - p123) * t + p123

        return CubicBezierCurve(p1, p12, p123, p1234), CubicBezierCurve(p1234, p234, p34, p4)


if __name__ == '__main__':
    import matplotlib.pyplot as plt

    cp = [(0, 0), (10, 0), (20, 20), (30, 20)]
    curve = CubicBezierCurve(*cp)
    curve2, curve3 = curve.split(0.1)

    t = np.linspace(0, 1, num=100)

    curve_eval = curve.evaluate(t)
    curve2_eval = curve2.evaluate(t)
    curve3_eval = curve3.evaluate(t)

    plt.figure()
    plt.plot(curve_eval[0, :], curve_eval[1, :])
    plt.plot(curve2_eval[0, :], curve2_eval[1, :])
    plt.plot(curve3_eval[0, :], curve3_eval[1, :])
    plt.show()
