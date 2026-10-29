"""JSON I/O that refuses floating point in both directions."""
import json


class FloatInJson(ValueError):
    pass


def _reject_float(token):
    raise FloatInJson("floating-point token in JSON input: " + token)


def _reject_const(token):
    raise FloatInJson("non-finite constant in JSON input: " + token)


def assert_no_float(obj, path="$"):
    t = type(obj)
    if t is dict:
        for k, v in obj.items():
            if type(k) is not str:
                raise FloatInJson("non-string key at " + path)
            assert_no_float(v, path + "." + k)
    elif t is list or t is tuple:
        for i, v in enumerate(obj):
            assert_no_float(v, path + "[" + str(i) + "]")
    elif t in (int, str, bool) or obj is None:
        return
    else:
        raise FloatInJson("disallowed type " + t.__name__ + " at " + path)


def dumps(obj):
    assert_no_float(obj)
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def dump(obj, path):
    text = dumps(obj)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def dump_lines(records, path):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            assert_no_float(rec)
            fh.write(json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")


def loads(text):
    return json.loads(text, parse_float=_reject_float, parse_constant=_reject_const)


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return loads(fh.read())
