import itertools
import sys
import threading
import time

### ---------- 共有状態 ----------

TAPE_INIT = 30_000  # 初期テープ長（足りなければ自動拡張）
tape = [0] * TAPE_INIT  # 共有テープ
cell_locks: dict[int, threading.RLock] = {}  # idx → threading.RLock
cell_locks_mu = threading.Lock()  # cell_locks への排他


def _get_lock(idx: int) -> threading.RLock:
    """セルごとの RLock を遅延生成して返す"""
    with cell_locks_mu:
        return cell_locks.setdefault(idx, threading.RLock())


### ---------- ヘルパ: パース & ユーティリティ ----------

BF_BASE = set("><+-.,[]")  # 素の Brainfuck 命令
EXTRA = set("{}|()~")  # Brainfork 追加
TOK = BF_BASE | EXTRA  # サポート記号


def strip_comments(src: str) -> str:
    """行頭コメント ';' から改行までを除去し、無効文字も捨てる"""
    cleaned = []
    for line in src.splitlines():
        if ";" in line:
            line = line[: line.index(";")]
        cleaned.append("".join(ch for ch in line if ch in TOK))
    return "".join(cleaned)


def build_jump_map(code: str) -> dict:
    """ループ [ ] のジャンプテーブルを作る"""
    stack, jumps = [], {}
    for i, ch in enumerate(code):
        if ch == "[":
            stack.append(i)
        elif ch == "]":
            if not stack:
                raise SyntaxError("']' without matching '['")
            j = stack.pop()
            jumps[i] = j - 1  # 戻りは j-1（while ループの ++ 分で結果 j に）
            jumps[j] = i  # 進みは i
    if stack:
        raise SyntaxError("'[' without matching ']'")
    return jumps


def extract_block(code: str, pos: int) -> tuple[str, int]:
    """'{' の位置 pos から対応 '}' 直前までを抜き出し、(内容, '}' の idx) を返す"""
    depth = 0
    for i in range(pos, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return code[pos + 1 : i], i
    raise SyntaxError("Unmatched '{'")


def split_parallel(segment: str) -> list[str]:
    """{ ... } 内部をトップレベルの '|' で分割"""
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in segment:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == "|" and depth == 0:
            parts.append("".join(buf))
            buf.clear()
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return parts


### ---------- 実行スレッド ----------


class BrainforkThread(threading.Thread):
    _id_iter = itertools.count()

    def __init__(self, code: str, inp):
        super().__init__(daemon=False)
        self.code = code
        self.dp = 0  # data pointer
        self.ip = 0  # instruction pointer
        self.lock_stack: list[threading.RLock] = []
        self.jumps = build_jump_map(code)
        self.inp = inp
        self.name = f"BF-{next(self._id_iter)}"

    # ---- tape helpers ----
    def _ensure_len(self, idx: int):
        if idx >= len(tape):
            tape.extend([0] * (idx - len(tape) + 1))

    def run(self):  # ← スレッドの本体
        c = self.code
        while self.ip < len(c):
            ch = c[self.ip]
            if ch == ">":
                self.dp += 1
                self._ensure_len(self.dp)
            elif ch == "<":
                self.dp = max(0, self.dp - 1)
            elif ch == "+":
                tape[self.dp] = (tape[self.dp] + 1) & 0xFF
            elif ch == "-":
                tape[self.dp] = (tape[self.dp] - 1) & 0xFF
            elif ch == ".":
                sys.stdout.write(chr(tape[self.dp]))
                sys.stdout.flush()
            elif ch == ",":
                ch_in = self.inp.read(1)
                tape[self.dp] = ord(ch_in) if ch_in else 0
            elif ch == "[":
                if tape[self.dp] == 0:
                    self.ip = self.jumps[self.ip]
            elif ch == "]":
                if tape[self.dp] != 0:
                    self.ip = self.jumps[self.ip]
            elif ch == "~":
                time.sleep(0.1)
            elif ch == "(":  # lock acquire
                lk = _get_lock(self.dp)
                lk.acquire()
                self.lock_stack.append(lk)
            elif ch == ")":  # lock release
                if not self.lock_stack:
                    raise RuntimeError(f"{self.name}: unlock without lock")
                self.lock_stack.pop().release()
            elif ch == "{":  # parallel block
                segment, end = extract_block(c, self.ip)
                parts = split_parallel(segment)
                threads = [BrainforkThread(p, self.inp) for p in parts]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                self.ip = end  # '}' の位置にジャンプ
            # 他の文字は無視（コメント処理済み）
            self.ip += 1

        if self.lock_stack:
            raise RuntimeError(f"{self.name}: locks not released before end")


### ---------- エントリポイント ----------


def main():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1], encoding="utf-8") as f:
            src = f.read()
    else:
        src = sys.stdin.read()

    code = strip_comments(src)
    top = BrainforkThread(code, sys.stdin)
    top.start()
    top.join()


if __name__ == "__main__":
    main()
