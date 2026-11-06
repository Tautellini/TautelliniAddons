"""Check Lua 5.1 files for syntax errors, for machines without luac or luacheck.

Usage: py -3.13 tools/luasyntax.py <file.lua>...   (exit code 1 on the first error per file)
       py -3.13 tools/luasyntax.py --selftest
It parses the full Lua 5.1 grammar but does not build a tree, check globals or know the WoW API.
"""
import re
import sys

KEYWORDS = {"and", "break", "do", "else", "elseif", "end", "false", "for", "function", "if", "in", "local",
            "nil", "not", "or", "repeat", "return", "then", "true", "until", "while"}
SYMBOLS = ["...", "..", "==", "~=", "<=", ">=", "+", "-", "*", "/", "%", "^", "#", "<", ">", "=",
           "(", ")", "{", "}", "[", "]", ";", ":", ",", "."]
BINARY = {"or": 1, "and": 2, "<": 3, ">": 3, "<=": 3, ">=": 3, "~=": 3, "==": 3, "..": 5,
          "+": 6, "-": 6, "*": 7, "/": 7, "%": 7, "^": 10}
RIGHT = {"..": 4, "^": 9}  # right associative: right side binds at this level
UNARY_LEVEL = 8
NUMBER = re.compile(r"0[xX][0-9a-fA-F]+|(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
LONG_OPEN = re.compile(r"\[(=*)\[")


class LuaSyntaxError(Exception):
    pass


def tokenize(src):
    """List of (kind, value, line). kind is name, keyword, number, string, symbol or eof."""
    out, i, line, n = [], 0, 1, len(src)
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
        elif c in " \t\r":
            i += 1
        elif src.startswith("--", i):
            m = LONG_OPEN.match(src, i + 2)
            if m:
                end = src.find("]" + m.group(1) + "]", m.end())
                if end < 0:
                    raise LuaSyntaxError(f"line {line}: unfinished long comment")
                line += src.count("\n", i, end)
                i = end + len(m.group(0))
            else:
                j = src.find("\n", i)
                i = n if j < 0 else j
        elif c == "[" and LONG_OPEN.match(src, i):
            m = LONG_OPEN.match(src, i)
            end = src.find("]" + m.group(1) + "]", m.end())
            if end < 0:
                raise LuaSyntaxError(f"line {line}: unfinished long string")
            out.append(("string", src[m.end():end], line))
            line += src.count("\n", i, end)
            i = end + len(m.group(0))
        elif c in "'\"":
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == "\\":
                    j += 1
                elif src[j] == "\n":
                    raise LuaSyntaxError(f"line {line}: unfinished string")
                j += 1
            if j >= n:
                raise LuaSyntaxError(f"line {line}: unfinished string")
            out.append(("string", src[i + 1:j], line))
            i = j + 1
        elif c.isdigit() or (c == "." and i + 1 < n and src[i + 1].isdigit()):
            m = NUMBER.match(src, i)
            out.append(("number", m.group(0), line))
            i = m.end()
        elif NAME.match(src, i):
            m = NAME.match(src, i)
            word = m.group(0)
            out.append(("keyword" if word in KEYWORDS else "name", word, line))
            i = m.end()
        else:
            sym = next((s for s in SYMBOLS if src.startswith(s, i)), None)
            if sym is None:
                raise LuaSyntaxError(f"line {line}: unexpected character {c!r}")
            out.append(("symbol", sym, line))
            i += len(sym)
    out.append(("eof", "<eof>", line))
    return out


class Parser:
    def __init__(self, tokens):
        self.t, self.p = tokens, 0

    def peek(self, offset=0):
        return self.t[min(self.p + offset, len(self.t) - 1)]

    def check(self, value):
        kind, v, _ = self.peek()
        return v == value and kind in ("keyword", "symbol")

    def accept(self, value):
        if self.check(value):
            self.p += 1
            return True
        return False

    def expect(self, value, opener=None):
        if not self.accept(value):
            _, v, line = self.peek()
            where = f" (to close {opener[0]!r} at line {opener[1]})" if opener else ""
            raise LuaSyntaxError(f"line {line}: {value!r} expected{where} near {v!r}")

    def name(self):
        kind, v, line = self.peek()
        if kind != "name":
            raise LuaSyntaxError(f"line {line}: name expected near {v!r}")
        self.p += 1

    def chunk(self):
        self.block()
        if self.peek()[0] != "eof":
            _, v, line = self.peek()
            raise LuaSyntaxError(f"line {line}: unexpected {v!r}")

    def block(self):
        while not self.block_ends():
            if self.check("return") or self.check("break"):
                last = self.peek()[1]
                self.p += 1
                if last == "return" and not self.block_ends() and not self.check(";"):
                    self.explist()
                self.accept(";")
                if not self.block_ends():
                    _, v, line = self.peek()
                    raise LuaSyntaxError(f"line {line}: {last!r} must be the last statement in a block, near {v!r}")
                return
            self.statement()
            self.accept(";")

    def block_ends(self):
        kind, v, _ = self.peek()
        return kind == "eof" or (kind == "keyword" and v in ("end", "else", "elseif", "until"))

    def statement(self):
        kind, v, line = self.peek()
        if kind == "keyword":
            if v == "do":
                self.p += 1
                self.block()
                self.expect("end", ("do", line))
                return
            if v == "while":
                self.p += 1
                self.expr()
                self.expect("do")
                self.block()
                self.expect("end", ("while", line))
                return
            if v == "repeat":
                self.p += 1
                self.block()
                self.expect("until", ("repeat", line))
                self.expr()
                return
            if v == "if":
                self.p += 1
                self.expr()
                self.expect("then")
                self.block()
                while self.accept("elseif"):
                    self.expr()
                    self.expect("then")
                    self.block()
                if self.accept("else"):
                    self.block()
                self.expect("end", ("if", line))
                return
            if v == "for":
                self.p += 1
                self.name()
                if self.accept("="):
                    self.expr()
                    self.expect(",")
                    self.expr()
                    if self.accept(","):
                        self.expr()
                else:
                    while self.accept(","):
                        self.name()
                    self.expect("in")
                    self.explist()
                self.expect("do")
                self.block()
                self.expect("end", ("for", line))
                return
            if v == "function":
                self.p += 1
                self.name()
                while self.accept("."):
                    self.name()
                if self.accept(":"):
                    self.name()
                self.funcbody(line)
                return
            if v == "local":
                self.p += 1
                if self.accept("function"):
                    self.name()
                    self.funcbody(line)
                    return
                self.name()
                while self.accept(","):
                    self.name()
                if self.accept("="):
                    self.explist()
                return
        # Expression statement: an assignment or a call.
        is_call = self.suffixed()
        if self.check("=") or self.check(","):
            if is_call:
                raise LuaSyntaxError(f"line {line}: cannot assign to a function call")
            while self.accept(","):
                if self.suffixed():
                    raise LuaSyntaxError(f"line {line}: cannot assign to a function call")
            self.expect("=")
            self.explist()
        elif not is_call:
            raise LuaSyntaxError(f"line {line}: syntax error, a statement must be an assignment or a call")

    def funcbody(self, line):
        self.expect("(")
        if not self.check(")"):
            while True:
                if self.accept("..."):
                    break
                self.name()
                if not self.accept(","):
                    break
        self.expect(")")
        self.block()
        self.expect("end", ("function", line))

    def explist(self):
        self.expr()
        while self.accept(","):
            self.expr()

    def primary(self):
        kind, v, line = self.peek()
        if kind == "name":
            self.p += 1
        elif self.accept("("):
            self.expr()
            self.expect(")", ("(", line))
        else:
            raise LuaSyntaxError(f"line {line}: unexpected symbol near {v!r}")

    def suffixed(self):
        """Parse a prefix expression. Returns True if it ends in a call."""
        self.primary()
        is_call = False
        while True:
            kind, v, line = self.peek()
            if self.accept("."):
                self.name()
                is_call = False
            elif self.accept("["):
                self.expr()
                self.expect("]", ("[", line))
                is_call = False
            elif self.accept(":"):
                self.name()
                self.args()
                is_call = True
            elif self.check("(") or self.check("{") or kind == "string":
                self.args()
                is_call = True
            else:
                return is_call

    def args(self):
        kind, v, line = self.peek()
        if kind == "string":
            self.p += 1
        elif self.check("{"):
            self.table()
        else:
            self.expect("(")
            if not self.check(")"):
                self.explist()
            self.expect(")", ("(", line))

    def table(self):
        line = self.peek()[2]
        self.expect("{")
        while not self.check("}"):
            if self.check("["):
                self.p += 1
                self.expr()
                self.expect("]")
                self.expect("=")
                self.expr()
            elif self.peek()[0] == "name" and self.peek(1)[1] == "=" and self.peek(1)[0] == "symbol":
                self.p += 2
                self.expr()
            else:
                self.expr()
            if not (self.accept(",") or self.accept(";")):
                break
        self.expect("}", ("{", line))

    def simple(self):
        kind, v, line = self.peek()
        if kind in ("number", "string") or (kind == "keyword" and v in ("nil", "true", "false")) or self.check("..."):
            self.p += 1
        elif self.check("{"):
            self.table()
        elif self.accept("function"):
            self.funcbody(line)
        else:
            self.suffixed()

    def expr(self, limit=0):
        if self.check("not") or self.check("-") or self.check("#"):
            self.p += 1
            self.expr(UNARY_LEVEL)
        else:
            self.simple()
        while True:
            kind, v, _ = self.peek()
            level = BINARY.get(v) if kind in ("symbol", "keyword") else None
            if level is None or level <= limit:
                return
            self.p += 1
            self.expr(RIGHT.get(v, level))


def check_source(src):
    Parser(tokenize(src)).chunk()


def selftest():
    good = '''local a, b = 1, "x" .. [[long
string]] -- comment
--[==[ long
comment ]==]
local t = { 1, x = 2, [3] = function(...) return ... end; "s" }
function t.f:m(a, ...) if a then return a elseif not a then return -1 else return #t end end
for i = 1, 10, 2 do t[i] = i ^ 2 ^ 3 end
for k, v in pairs(t) do print(k, v) end
while false do break end
repeat local x = 1 until x == 1
f"str" f{1} a.b.c = (1 + 2) * 3 ~= 4 and 5 or 6
'''
    check_source(good)
    bad = {
        "local function f() if x then end": "'end' expected",
        "x = = 1": "unexpected symbol",
        "f() = 1": "cannot assign",
        "x + 1": "statement must be",
        "return 1 print(2)": "must be the last statement",
        "local s = 'abc": "unfinished string",
        "t = { a = 1 b = 2 }": "'}' expected",
    }
    for src, message in bad.items():
        try:
            check_source(src)
        except LuaSyntaxError as e:
            assert message in str(e), (src, str(e))
        else:
            raise AssertionError(f"no error for {src!r}")
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit()
    failed = False
    for path in sys.argv[1:]:
        try:
            check_source(open(path, encoding="utf-8").read())
            print(f"ok      {path}")
        except LuaSyntaxError as e:
            print(f"ERROR   {path}: {e}")
            failed = True
    sys.exit(1 if failed else 0)
