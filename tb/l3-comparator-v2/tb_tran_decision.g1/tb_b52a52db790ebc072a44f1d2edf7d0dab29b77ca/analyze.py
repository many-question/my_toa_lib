#!/usr/bin/env python3
"""Analysis script of a TOA testbench, written by toa-virtuoso from the outputs of a Virtuoso
ADE / Maestro test.

Called as `analyze.py <results> <output>`: reads the simulation results of one set of conditions
(Spectre PSF ASCII files, `-format psfascii`) from the directory <results>, and writes
<output>/metrics.json (one number per metric) and <output>/evidence/ (the waveforms the metrics
were computed from, as CSV).

Standard library only (Python 3.6 or later). The first part is a small runtime: a reader of PSF
ASCII and the functions of the Virtuoso calculator that the metrics use, written to give the
same numbers. The last part, METRICS, is the outputs of the test translated by toa-virtuoso.
"""

import json
import math
import os
import re
import sys

# --------------------------------------------------------------------------------------------
# PSF ASCII


class PsfError(Exception):
    pass


_TOKEN = re.compile(r'\s*(?:"((?:[^"\\]|\\.)*)"|(\()|(\))|([^\s()"]+))')


def _tokens(text):
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            break
        pos = m.end()
        if m.group(1) is not None:
            yield ("str", m.group(1))
        elif m.group(2):
            yield ("(", None)
        elif m.group(3):
            yield (")", None)
        elif m.group(4) is not None:
            yield ("word", m.group(4))


def _number(word):
    try:
        return float(word)
    except ValueError:
        raise PsfError("not a number: %r" % word)


class Psf(object):
    """One PSF ASCII file: header properties, the sweep, and the traces by name."""

    def __init__(self, path):
        self.path = path
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        sections = {}
        current = None
        lines = []
        for line in text.split("\n"):
            word = line.strip()
            if word in ("HEADER", "TYPE", "SWEEP", "TRACE", "VALUE", "END"):
                if current is not None:
                    sections[current] = "\n".join(lines)
                current, lines = word, []
            else:
                lines.append(line)
        if current is not None and current != "END":
            sections[current] = "\n".join(lines)
        self.header = self._props(sections.get("HEADER", ""))
        self.types = self._types(sections.get("TYPE", ""))
        self.sweep = None
        sweep = list(_tokens(sections.get("SWEEP", "")))
        if sweep and sweep[0][0] == "str":
            self.sweep = sweep[0][1]
        self.trace_types = []
        toks = list(_tokens(sections.get("TRACE", "")))
        i = 0
        while i < len(toks):
            if toks[i][0] == "str" and i + 1 < len(toks) and toks[i + 1][0] == "str":
                self.trace_types.append((toks[i][1], toks[i + 1][1]))
                i += 2
                if i < len(toks) and toks[i] == ("word", "PROP"):
                    i = self._skip_group(toks, i + 1)
            else:
                i += 1
        self.x = []
        self.traces = {}
        self.scalars = {}
        self._values(sections.get("VALUE", ""))

    @staticmethod
    def _skip_group(toks, i):
        depth = 0
        while i < len(toks):
            if toks[i][0] == "(":
                depth += 1
            elif toks[i][0] == ")":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return i

    @staticmethod
    def _props(text):
        out = {}
        toks = list(_tokens(text))
        i = 0
        while i + 1 < len(toks):
            if toks[i][0] == "str":
                k, (kind, v) = toks[i][1], toks[i + 1]
                out[k] = v if kind == "str" else _maybe_number(v)
                i += 2
            else:
                i += 1
        return out

    @staticmethod
    def _types(text):
        # name -> "FLOAT", "COMPLEX" or "STRUCT"
        out = {}
        toks = list(_tokens(text))
        i = 0
        depth = 0
        while i < len(toks):
            kind, v = toks[i]
            if kind == "(":
                depth += 1
            elif kind == ")":
                depth -= 1
            elif depth == 0 and kind == "str" and i + 1 < len(toks) and toks[i + 1][0] == "word":
                if toks[i + 1][1] in ("FLOAT", "COMPLEX", "STRUCT", "INT", "STRING"):
                    out[v] = toks[i + 1][1]
            i += 1
        return out

    def _values(self, text):
        toks = list(_tokens(text))
        i = 0
        while i < len(toks):
            kind, name = toks[i]
            if kind != "str":
                i += 1
                continue
            i += 1
            # a non-swept value is "name" "type" value
            if i < len(toks) and toks[i][0] == "str" and self.sweep is None:
                i += 1
            if i >= len(toks):
                break
            if toks[i][0] == "(":
                j = i + 1
                nums = []
                while j < len(toks) and toks[j][0] != ")":
                    if toks[j][0] == "word":
                        nums.append(_number(toks[j][1]))
                    j += 1
                i = j + 1
                ttype = self.types.get(dict(self.trace_types).get(name, ""), "")
                value = complex(nums[0], nums[1]) if ttype == "COMPLEX" and len(nums) == 2 else nums
            else:
                value = _maybe_number(toks[i][1])
                i += 1
            if i < len(toks) and toks[i] == ("word", "PROP"):
                i = self._skip_group(toks, i + 1)
            if self.sweep is not None and name == self.sweep:
                self.x.append(value)
            elif self.sweep is not None:
                self.traces.setdefault(name, []).append(value)
            else:
                self.scalars[name] = value

    def wave(self, name):
        if name not in self.traces:
            raise PsfError("%s has no signal %s" % (os.path.basename(self.path), name))
        ys = self.traces[name]
        if ys and isinstance(ys[0], list):
            raise PsfError("%s: %s is not a waveform" % (os.path.basename(self.path), name))
        return Wave(self.x[: len(ys)], ys, name)


def _maybe_number(word):
    try:
        return float(word)
    except (TypeError, ValueError):
        return word


class Results(object):
    """The PSF ASCII files of one simulation, by analysis."""

    def __init__(self, directory):
        self.dir = directory
        self._cache = {}
        self.used = []  # (kind, label, wave): what the metrics read, written as evidence
        self._conditions = None  # <results>/conditions.json, read when needed

    def file(self, *names):
        for n in names:
            p = os.path.join(self.dir, n)
            if os.path.isfile(p):
                if p not in self._cache:
                    self._cache[p] = Psf(p)
                return self._cache[p]
        raise PsfError("no results file %s in %s" % (" or ".join(names), self.dir))

    def analysis(self, name, kind):
        """The file of the analysis `name`: kind is tran, td.pss, pnoise, ac, noise, dc... An
        analysis inside a sweep has one file per point, `<sweep>-000_<name>.<kind>` and so on:
        that gives a Family of files, in the order of the sweep."""
        cands = {
            "tran": [name + ".tran.tran", name + ".tran"],
            "td.pss": [name + ".td.pss"],
            "fd.pss": [name + ".fd.pss"],
            "pnoise": [name + ".pnoise"],
            "ac": [name + ".ac"],
            "noise": [name + ".noise"],
            "dc": [name + ".dc"],
        }.get(kind, [name + "." + kind])
        for c in cands:
            if os.path.isfile(os.path.join(self.dir, c)):
                return self.file(c)
        swept = []
        if os.path.isdir(self.dir):
            for c in cands:
                pat = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*-(\d+)_" + re.escape(c) + "$")
                swept = sorted((int(m.group(1)), f) for f in os.listdir(self.dir) for m in [pat.match(f)] if m)
                if swept:
                    break
        if swept:
            return Family(self.file(f) for _, f in swept)
        return self.file(*cands)

    def conditions(self):
        """<results>/conditions.json: the conditions of the run and its probes (tb, 7.6)."""
        if self._conditions is None:
            path = os.path.join(self.dir, "conditions.json")
            self._conditions = {}
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as f:
                    self._conditions = json.load(f)
        return self._conditions

    def candidates(self, ade_name):
        """The names a signal may have in the results: a name with a probe, <inst>.<probe>, also
        as the net that the run gives the probe."""
        probes = self.conditions().get("probes") or {}
        out = []
        for c in signal_names(ade_name):
            out.append(c)
            head, _, last = c.rpartition(".")
            if head and last in probes:
                out.append(head + "." + probes[last])
        return out

    def signal(self, psf, ade_name):
        """A waveform by its name in ADE: /net, /inst/net, /inst/TERM."""
        if isinstance(psf, Family):
            return Family(self.signal(p, ade_name) for p in psf)
        for cand in self.candidates(ade_name):
            if cand in psf.traces:
                return psf.wave(cand)
        raise PsfError("%s has no signal for %s (tried %s)" % (os.path.basename(psf.path), ade_name,
                                                               ", ".join(self.candidates(ade_name))))

    def note(self, kind, label, wave):
        if isinstance(wave, Family):
            for i, w in enumerate(wave):
                self.used.append((kind, "%s [%d]" % (label, i), w))
        else:
            self.used.append((kind, label, wave))
        return wave


# The names the netlist saved for the outputs of the test, as ADE wrote them; filled in by
# toa-virtuoso. A name not listed here is tried as a net (/a/b -> a.b) and as a terminal.
SIGNALS = {}
# The analyses of the test by type: {"pss": "pss", "pnoise": "pnoise", "tran": "tran"}.
ANALYSES = {}
TERMINALS = {"PLUS": "p", "MINUS": "n"}


def signal_names(ade_name):
    out = []
    if ade_name in SIGNALS:
        out.append(SIGNALS[ade_name])
    parts = [p for p in ade_name.split("/") if p]
    if parts:
        out.append(".".join(parts))
        if len(parts) >= 2:
            inst, term = ".".join(parts[:-1]), parts[-1]
            out.append("%s:%s" % (inst, TERMINALS.get(term, term)))
            out.append("%s:%s" % (inst, term.lower()))
    return out


# --------------------------------------------------------------------------------------------
# Waveforms and the functions of the Virtuoso calculator


class CalcError(Exception):
    pass


class Wave(object):
    def __init__(self, x, y, label=""):
        if len(x) != len(y):
            raise CalcError("a waveform with %d x and %d y values" % (len(x), len(y)))
        self.x = list(x)
        self.y = list(y)
        self.label = label

    def __len__(self):
        return len(self.x)

    def at(self, x):
        xs, ys = self.x, self.y
        if not xs:
            raise CalcError("an empty waveform")
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        lo, hi = 0, len(xs) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if xs[mid] <= x:
                lo = mid
            else:
                hi = mid
        x0, x1 = xs[lo], xs[hi]
        if x1 == x0:
            return ys[lo]
        return ys[lo] + (ys[hi] - ys[lo]) * (x - x0) / (x1 - x0)

    def _op(self, other, f):
        if isinstance(other, Family):
            return NotImplemented
        if isinstance(other, Wave):
            if other.x == self.x:
                return Wave(self.x, [f(a, b) for a, b in zip(self.y, other.y)])
            xs = sorted(set(self.x) | set(other.x))
            return Wave(xs, [f(self.at(x), other.at(x)) for x in xs])
        return Wave(self.x, [f(a, other) for a in self.y])

    def _rop(self, other, f):
        return Wave(self.x, [f(other, a) for a in self.y])

    def __add__(self, o):
        return self._op(o, lambda a, b: a + b)

    def __radd__(self, o):
        return self._rop(o, lambda a, b: a + b)

    def __sub__(self, o):
        return self._op(o, lambda a, b: a - b)

    def __rsub__(self, o):
        return self._rop(o, lambda a, b: a - b)

    def __mul__(self, o):
        return self._op(o, lambda a, b: a * b)

    def __rmul__(self, o):
        return self._rop(o, lambda a, b: a * b)

    def __truediv__(self, o):
        return self._op(o, lambda a, b: a / b)

    def __rtruediv__(self, o):
        return self._rop(o, lambda a, b: a / b)

    def __neg__(self):
        return Wave(self.x, [-a for a in self.y])

    def __pow__(self, o):
        return self._op(o, lambda a, b: a ** b)


class Family(list):
    """The results of a swept analysis, one item per point of the sweep, such as the runs of a
    transient noise analysis: arithmetic and the functions apply item by item, and average() of
    a family of numbers is their mean, as in the calculator."""

    def _op(self, o, f):
        if isinstance(o, Family):
            if len(o) != len(self):
                raise CalcError("families of %d and %d items" % (len(self), len(o)))
            return Family(f(a, b) for a, b in zip(self, o))
        return Family(f(a, o) for a in self)

    def _rop(self, o, f):
        return Family(f(o, a) for a in self)

    def __add__(self, o):
        return self._op(o, lambda a, b: a + b)

    def __radd__(self, o):
        return self._rop(o, lambda a, b: a + b)

    def __sub__(self, o):
        return self._op(o, lambda a, b: a - b)

    def __rsub__(self, o):
        return self._rop(o, lambda a, b: a - b)

    def __mul__(self, o):
        return self._op(o, lambda a, b: a * b)

    def __rmul__(self, o):
        return self._rop(o, lambda a, b: a * b)

    def __truediv__(self, o):
        return self._op(o, lambda a, b: a / b)

    def __rtruediv__(self, o):
        return self._rop(o, lambda a, b: a / b)

    def __neg__(self):
        return Family(-a for a in self)

    def __pow__(self, o):
        return self._op(o, lambda a, b: a ** b)


def _lift(f):
    """f applied to each item when its first argument is a Family."""
    def g(w, *a, **k):
        if isinstance(w, Family):
            return Family(g(x, *a, **k) for x in w)
        return f(w, *a, **k)
    g.__name__, g.__doc__ = f.__name__, f.__doc__
    return g


def _map(v, f):
    if isinstance(v, Family):
        return Family(_map(x, f) for x in v)
    if isinstance(v, Wave):
        return Wave(v.x, [f(a) for a in v.y])
    return f(v)


def _wave(v, fn):
    if not isinstance(v, Wave):
        raise CalcError("%s needs a waveform" % fn)
    if not len(v):
        raise CalcError("%s of an empty waveform" % fn)
    return v


def sqrt(v):
    return _map(v, math.sqrt)


def abs_(v):
    return _map(v, abs)


def mag(v):
    return _map(v, abs)


def dB20(v):
    return _map(v, lambda a: 20 * math.log10(abs(a)))


def dB10(v):
    return _map(v, lambda a: 10 * math.log10(abs(a)))


def exp(v):
    return _map(v, math.exp)


def log10(v):
    return _map(v, math.log10)


def int_(v):
    """int: the integer part, toward zero."""
    return _map(v, lambda a: float(int(a)))


@_lift
def clip(w, start=None, stop=None, interpolate=True):
    w = _wave(w, "clip")
    lo = w.x[0] if start is None else start
    hi = w.x[-1] if stop is None else stop
    xs, ys = [], []
    if interpolate and lo > w.x[0]:
        xs.append(lo)
        ys.append(w.at(lo))
    for x, y in zip(w.x, w.y):
        if lo <= x <= hi and not (xs and x == xs[-1]):
            xs.append(x)
            ys.append(y)
    if interpolate and hi < w.x[-1] and (not xs or xs[-1] != hi):
        xs.append(hi)
        ys.append(w.at(hi))
    return Wave(xs, ys)


@_lift
def integ(w, start=None, stop=None, title=None):
    """The integral by the trapezoidal rule, from start to stop (the ends interpolated)."""
    w = _wave(w, "integ")
    c = clip(w, start, stop)
    s = 0.0
    for i in range(1, len(c.x)):
        s += (c.x[i] - c.x[i - 1]) * (c.y[i] + c.y[i - 1]) / 2.0
    return s


def average(w, start=None, stop=None):
    """The average over x: the integral divided by the length; of a number, the number; of a
    family of numbers, their mean."""
    if isinstance(w, Family):
        if w and not any(isinstance(x, (Wave, Family)) for x in w):
            return sum(w) / len(w)
        return Family(average(x, start, stop) for x in w)
    if not isinstance(w, Wave):
        return w
    c = clip(w, start, stop)
    if len(c.x) < 2 or c.x[-1] == c.x[0]:
        return c.y[0]
    return integ(c) / (c.x[-1] - c.x[0])


@_lift
def ymax(w):
    return max(_wave(w, "ymax").y)


@_lift
def ymin(w):
    return min(_wave(w, "ymin").y)


@_lift
def peakToPeak(w):
    w = _wave(w, "peakToPeak")
    return max(w.y) - min(w.y)


@_lift
def value(w, x):
    if not isinstance(w, Wave):
        return w
    return w.at(x)


@_lift
def cross(w, threshold, n=1, edge="either", multiple=None, xname=None, tol=None):
    """The x where w crosses threshold for the n-th time in the given direction (the
    crossing interpolated linearly), as the calculator's cross() does."""
    w = _wave(w, "cross")
    n = int(n)
    if multiple:
        raise CalcError("cross with ?multiple is not supported")
    found = []
    for i in range(1, len(w.x)):
        a, b = w.y[i - 1] - threshold, w.y[i] - threshold
        rising = a < 0 <= b
        falling = a > 0 >= b
        if (edge == "rising" and rising) or (edge == "falling" and falling) or \
                (edge in ("either", None) and (rising or falling)):
            if b == a:
                x = w.x[i]
            else:
                x = w.x[i - 1] + (w.x[i] - w.x[i - 1]) * (0 - a) / (b - a)
            found.append(x)
    if n < 0:
        if len(found) >= -n:
            return found[n]
    elif 1 <= n <= len(found):
        return found[n - 1]
    raise CalcError("cross: crossing %d of %g (%s) not found" % (n, threshold, edge))


def _analysis_name(kind, result=None):
    return result or ANALYSES.get(kind) or kind


def vtime(R, analysis, signal):
    """vtime('pss "/net"): the periodic steady state of a voltage over one period."""
    if analysis != "pss":
        raise CalcError("vtime of %s is not supported" % analysis)
    psf = R.analysis(_analysis_name("pss"), "td.pss")
    return R.note("waveform", "pss " + signal, R.signal(psf, signal))


def itime(R, analysis, signal):
    """itime('pss "/inst/TERM"): the periodic steady state of a terminal current."""
    return vtime(R, analysis, signal)


def VT(R, signal, result=None):
    psf = R.analysis(_analysis_name("tran", result), "tran")
    return R.note("waveform", "tran " + signal, R.signal(psf, signal))


IT = VT


def getData(R, signal, result=None):
    kind = {"tran": "tran", "pss": "td.pss", "pnoise": "pnoise", "ac": "ac", "noise": "noise", "dc": "dc"}
    name = result or "tran"
    psf = R.analysis(name, kind.get(name, name))
    return R.note("waveform", "%s %s" % (name, signal), R.signal(psf, signal))


def rfInputNoise(R, unit="V/sqrt(Hz)", result=None):
    """rfInputNoise: the input-referred noise of a pnoise analysis with an input probe."""
    psf = R.analysis(_analysis_name("pnoise", result), "pnoise")
    w = psf.wave("in")
    if unit in ("V**2/Hz", "V^2/Hz"):
        w = Wave(w.x, [a * a for a in w.y])
    elif unit not in ("V/sqrt(Hz)", None):
        raise CalcError("rfInputNoise in %s is not supported" % unit)
    return R.note("spectrum", "pnoise input noise (%s)" % unit, w)


def VAR(R, name):
    """VAR("x"): the value of x in the conditions of this point, from <results>/conditions.json
    (the parameters first, then the options), as the run writes it."""
    cond = R.conditions()
    if not cond:
        raise CalcError("VAR(%s) needs %s, which the run did not write" % (name, os.path.join(R.dir, "conditions.json")))
    for slot in ("parameters", "options"):
        v = (cond.get(slot) or {}).get(name)
        if v is not None:
            return float(v)
    raise CalcError("VAR(%s): not in the conditions of this point" % name)


def rfOutputNoise(R, unit="V/sqrt(Hz)", result=None):
    psf = R.analysis(_analysis_name("pnoise", result), "pnoise")
    w = psf.wave("out")
    if unit in ("V**2/Hz", "V^2/Hz"):
        w = Wave(w.x, [a * a for a in w.y])
    return R.note("spectrum", "pnoise output noise (%s)" % unit, w)


# --------------------------------------------------------------------------------------------
# Running


def write_evidence(R, out_dir):
    ev = os.path.join(out_dir, "evidence")
    if not os.path.isdir(ev):
        os.makedirs(ev)
    listed = []
    seen = set()
    for kind, label, w in R.used:
        name = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_") + ".csv"
        if name in seen:
            continue
        seen.add(name)
        with open(os.path.join(ev, name), "w", encoding="utf-8", newline="\n") as f:
            f.write("x,y\n")
            for x, y in zip(w.x, w.y):
                f.write("%.12g,%.12g\n" % (x, y))
        listed.append({"path": "evidence/" + name, "kind": kind, "label": label})
    return listed


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: %s <results> <output>\n" % argv[0])
        return 2
    results, out_dir = argv[1], argv[2]
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    R = Results(results)
    metrics, errors = {}, {}
    for mid, fn in METRICS:
        try:
            v = fn(R)
            if isinstance(v, (Wave, Family)):
                raise CalcError("the expression gives a waveform, not a number")
            v = float(v)
            if math.isnan(v) or math.isinf(v):
                raise CalcError("not a finite number")
            metrics[mid] = v
        except (CalcError, PsfError, ValueError, ZeroDivisionError) as e:
            errors[mid] = str(e)
    evidence = write_evidence(R, out_dir)
    with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(metrics, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(os.path.join(out_dir, "evidence", "index.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"evidence": evidence, "errors": errors}, f, indent=1, sort_keys=True)
        f.write("\n")
    for mid, e in sorted(errors.items()):
        sys.stderr.write("%s: %s\n" % (mid, e))
    return 0


# --------------------------------------------------------------------------------------------
# The metrics, translated from the outputs of the test

SIGNALS.update({
    "/DCMPP": "DCMPP",
    "/DCMPN": "DCMPN",
})
ANALYSES.update({
    "tran": "tran",
})

METRICS = [
    # decision: average(int((value(VT("/DCMPP") 2e-10) + 0.45)))
    ("decision", lambda R: average(int_((value(VT(R, "/DCMPP"), 2e-10) + 0.45)))),
    # vout: average(value(VT("/DCMPP") 2e-10))
    ("vout", lambda R: average(value(VT(R, "/DCMPP"), 2e-10))),
    # tdel: average(cross((VT("/DCMPP") + VT("/DCMPN")) 0.45 1 "rising"))
    ("tdel", lambda R: average(cross((VT(R, "/DCMPP") + VT(R, "/DCMPN")), 0.45, 1.0, "rising"))),
]

if __name__ == "__main__":
    sys.exit(main(sys.argv))
