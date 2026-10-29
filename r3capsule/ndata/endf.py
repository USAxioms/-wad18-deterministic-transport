"""Integer-exact reader for ENDF-6 pointwise cross sections (MF3 TAB1) and resonance ranges.

ENDF floats are 11-column fields such as ' 1.000000-5' or ' 2.53+3' (exponent without E).
Values are converted to WAD-18 exactly where possible; values needing more than 18 fractional
digits are floored and counted in `inexact`.
"""
from .matxs import num


def fnum(field):
    t = field.strip()
    if not t:
        return 0, True
    if "E" not in t.upper():
        for j in range(len(t) - 1, 0, -1):
            if t[j] in "+-" and t[j - 1] not in "Ee":
                t = t[:j] + "E" + t[j:]
                break
    return num(t)


class Endf:
    def __init__(self, path):
        self.path = path
        self.inexact = 0
        self.sections = {}
        with open(path, encoding="ascii", errors="replace") as fh:
            for line in fh:
                if len(line) < 75:
                    continue
                try:
                    mf, mt = int(line[70:72]), int(line[72:75])
                except ValueError:
                    continue
                if mf > 0 and mt > 0:
                    self.sections.setdefault((mf, mt), []).append(line)

    def _f(self, line, k):
        v, ok = fnum(line[11 * k:11 * k + 11])
        if not ok:
            self.inexact += 1
        return v

    def _i(self, line, k):
        t = line[11 * k:11 * k + 11].strip()
        return int(t) if t else 0

    def tab1(self, mt, mf=3):
        """Return (interp ranges [(nbt,int)], [(E_wad, sigma_wad)]) for MF/MT."""
        L = self.sections[(mf, mt)]
        c = L[1]
        nr, npts = self._i(c, 4), self._i(c, 5)
        row = 2
        ranges = []
        while len(ranges) < nr:
            for k in range(0, 6, 2):
                if len(ranges) < nr:
                    ranges.append((self._i(L[row], k), self._i(L[row], k + 1)))
            row += 1
        pts = []
        while len(pts) < npts:
            for k in range(0, 6, 2):
                if len(pts) < npts:
                    pts.append((self._f(L[row], k), self._f(L[row], k + 1)))
            row += 1
        return ranges, pts

    def lrp(self):
        return self._i(self.sections[(1, 451)][0], 2)

    def _int_or_none(self, line, k):
        t = line[11 * k:11 * k + 11].strip()
        if not t:
            return 0
        u = t[1:] if t[0] in "+-" else t
        return int(t) if u.isdigit() else None

    def resonance_upper(self):
        """Upper energy of the resonance region: the largest EH over MF2/MT151 range records.

        A range record (EL, EH, LRU, LRF, NRO, NAPS) is recognised by integer fields 3-6 with
        LRU in {1, 2}, LRF in 1..7 and 0 <= EL < EH <= 200 MeV. A missed range lowers the cut
        (and shows up as bound violations); a spurious one raises it (and is reported as fewer
        groups checked) -- neither can produce a false pass silently."""
        if (2, 151) not in self.sections:
            return 0
        eh = 0
        top = 200000000 * 1000000000000000000
        for line in self.sections[(2, 151)][1:]:
            ints = [self._int_or_none(line, k) for k in range(2, 6)]
            if None in ints or ints[0] not in (1, 2) or not 1 <= ints[1] <= 7:
                continue
            el, eh_c = fnum(line[0:11])[0], fnum(line[11:22])[0]
            if 0 <= el < eh_c <= top:
                eh = max(eh, eh_c)
        return eh
