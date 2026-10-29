"""Integer-exact reader for NJOY MATXS (ASCII) multigroup libraries.

Every number is converted from its decimal text to WAD-18 without floating point. Values
whose decimal expansion needs more than 18 fractional digits are floored and counted in
`inexact` (reported, never hidden). The reader keeps raw words; transfer-matrix layout is
decoded by `matrix_p` only after it has been verified (see tests/test_ndata.py).
"""
from .. import wad18 as w

WAD_DIGITS = 18


def pow10(n):
    """10**n for n >= 0 without the power operator (exact integer)."""
    return int("1" + "0" * n)


def num(tok):
    """Decimal text (Fortran E or plain) -> (WAD int, exact flag).

    Floor rounding toward minus infinity when more than 18 fractional digits are needed."""
    t = tok.strip().upper().replace("D", "E")
    neg = t[0] == "-"
    if t[0] in "+-":
        t = t[1:]
    if "E" in t:
        mant, ex = t.split("E")
        ex = int(ex)
    else:
        mant, ex = t, 0
    ip, fp = mant.split(".") if "." in mant else (mant, "")
    digits = int((ip + fp) or "0")
    shift = WAD_DIGITS + ex - len(fp)
    if shift >= 0:
        mag, exact = digits * pow10(shift), True
        return (-mag if neg else mag), exact
    den = pow10(-shift)
    q, r = digits // den, digits % den
    if not neg:
        return q, r == 0
    return (-q if r == 0 else -(q + 1)), r == 0


class Matxs:
    def __init__(self, path):
        self.path = path
        self.inexact = 0
        recs = []
        with open(path, encoding="ascii") as fh:
            cur = None
            for line in fh:
                tag = line[:3]
                if len(tag) == 3 and tag[2] in "vd" and tag[:2].strip().isdigit():
                    cur = [tag.strip(), line[3:]]
                    recs.append(cur)
                else:
                    cur[1] += line
        self._parse(recs)

    def _nums(self, text):
        """Fixed-width numeric record: first line has 12 tag/blank columns, then 12-column fields."""
        out = []
        for j, line in enumerate(text.split("\n")):
            body = line.rstrip("\n")
            start = 9 if j == 0 else 0          # record text begins after the 3-char tag
            for c in range(start, len(body), 12):
                t = body[c:c + 12].strip()
                if not t:
                    continue
                v, ok = num(t)
                if not ok:
                    self.inexact += 1
                out.append(v)
        return out

    def _ints(self, text):
        return [int(t) for t in text.split()]

    def _parse(self, recs):
        i = 0
        hdr = self._ints(recs[1][1])                 # 1d
        self.npart, self.ntype, self.nholl, self.nmat, self.maxw, self.length = hdr[:6]
        t3 = recs[3][1].split()                      # 3d
        self.particles = t3[:self.npart]
        self.types = t3[self.npart:self.npart + self.ntype]
        self.material = t3[self.npart + self.ntype]
        ints = self._ints(" ".join(recs[3][1].split("\n")[1:]))
        self.ngrp = ints[:self.npart]
        self.type_in = ints[self.npart:self.npart + self.ntype]
        self.type_out = ints[self.npart + self.ntype:self.npart + 2 * self.ntype]
        i = 4
        self.bounds = {}
        for p in range(self.npart):                  # 4d per particle
            self.bounds[self.particles[p]] = self._nums(recs[i][1])
            i += 1
        t5 = recs[i][1].split()                      # 5d
        self.amass = num(t5[1])[0]
        self.sub = []
        k = 2
        while k < len(t5):
            temp, sigz = num(t5[k])[0], num(t5[k + 1])[0]
            itype, n1d, n2d, locs = (int(x) for x in t5[k + 2:k + 6])
            self.sub.append({"temp": temp, "sigz": sigz, "itype": itype, "n1d": n1d, "n2d": n2d,
                             "vectors": {}, "matrices": {}})
            k += 6
        i += 1
        for sm in self.sub:
            ng_in = self.ngrp[self.type_in[sm["itype"] - 1] - 1]
            ng_out = self.ngrp[self.type_out[sm["itype"] - 1] - 1]
            if sm["n1d"]:
                txt = recs[i][1]                     # 6d
                toks = txt.split()
                names = toks[:sm["n1d"]]
                rest = [int(x) for x in toks[sm["n1d"]:]]
                nfg, nlg = rest[:sm["n1d"]], rest[sm["n1d"]:2 * sm["n1d"]]
                i += 1
                data = []
                while i < len(recs) and recs[i][0] == "7d":
                    data += self._nums(recs[i][1])
                    i += 1
                pos = 0
                for nm, a, b in zip(names, nfg, nlg):
                    n = b - a + 1
                    sm["vectors"][nm] = (a, data[pos:pos + n])
                    pos += n
                assert pos == len(data), (self.path, "vector words", pos, len(data))
            for _ in range(sm["n2d"]):
                assert recs[i][0] == "8d", (self.path, recs[i][0])
                toks = recs[i][1].split()
                name = toks[0]
                v = [int(x) for x in toks[1:]]
                lord, jconst = v[0], v[1]
                jband, ijj = v[2:2 + ng_out], v[2 + ng_out:2 + 2 * ng_out]
                i += 1
                data = []
                while i < len(recs) and recs[i][0] == "9d":
                    data += self._nums(recs[i][1])
                    i += 1
                if i < len(recs) and recs[i][0] == "10d":
                    cdata = self._nums(recs[i][1])
                    i += 1
                else:
                    cdata = []
                need = lord * sum(jband)
                sm["matrices"][name] = {"lord": lord, "jconst": jconst, "jband": jband, "ijj": ijj,
                                        "data": data, "const": cdata, "words_expected": need,
                                        "ng_in": ng_in, "ng_out": ng_out}
        self.end_index = i

    def vector(self, name, sub=0):
        """Full-length (1..ng) vector, zeros outside its stored range."""
        a, vals = self.sub[sub]["vectors"][name]
        ng = self.ngrp[0]
        out = [0] * ng
        for j, x in enumerate(vals):
            out[a - 1 + j] = x
        return out
