#!/usr/bin/env python3
"""work-companion 可选清单工具。

它不是 skill 的依赖：没有它，SKILL.md 里的文本规则照样完整可执行。
它只做三件事：安全地读写清单、校验五字段、算出到期窗口。

用法示例：
  python3 ledger.py list
  python3 ledger.py add --content "周五交方案" --due 2026-11-20
  python3 ledger.py add --content "问他要报价" --followup --due 2026-11-18
  python3 ledger.py update --match "方案" --complete
  python3 ledger.py update --match "方案" --due 2026-11-27
  python3 ledger.py update --match "方案" --void
  python3 ledger.py update --match "方案" --delete
  python3 ledger.py due --within 3
  python3 ledger.py validate
  python3 ledger.py self-test

默认清单：用户主目录下的 work-companion/commitments.md。
可用 --file 指定别的路径（测试用）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

STATES = {"未完成", "已完成", "已作废", "等待对方", "待跟进"}
OPEN_STATES = {"未完成", "待跟进"}
WAITING_STATE = "等待对方"
DUE_EMPTY = "—"
DEFAULT_HISTORY = "未提"
LABELS = ("内容", "记录日", "到期日", "状态", "提醒历史")
LABEL_ALIASES = {
    "内容": "内容",
    "记录": "记录日",
    "记录日": "记录日",
    "到期": "到期日",
    "到期日": "到期日",
    "状态": "状态",
    "提醒": "提醒历史",
    "提醒历史": "提醒历史",
}
DEFAULT_LEDGER = Path.home() / "work-companion" / "commitments.md"

LABEL_RE = re.compile(r"(内容|记录日|记录|到期日|到期|提醒历史|提醒|状态)\s*[：:]")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COMPLETED_RE = re.compile(r"^已完成(?:\s*[（(:：]?\s*(\d{4}-\d{2}-\d{2})\s*[）)]?)?$")


class LedgerError(Exception):
    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


def today_str() -> str:
    return date.today().isoformat()


def parse_date(value: str) -> Optional[date]:
    value = (value or "").strip()
    if value in ("", DUE_EMPTY, "-", "无"):
        return None
    if not DATE_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def normalize_due(value: Optional[str]) -> str:
    value = (value or "").strip()
    if value in ("", DUE_EMPTY, "-", "无"):
        return DUE_EMPTY
    if value.lower() == "today":
        return today_str()
    if value.startswith("+"):
        try:
            days = int(value[1:])
        except ValueError as exc:
            raise LedgerError(f"无法识别的相对日期：{value}") from exc
        return (date.today() + timedelta(days=days)).isoformat()
    parsed = parse_date(value)
    if parsed is None:
        raise LedgerError(f"到期日必须是 YYYY-MM-DD 或 —，收到：{value}")
    return parsed.isoformat()


def state_is_valid(state: str) -> bool:
    state = (state or "").strip()
    if state in STATES:
        return True
    match = COMPLETED_RE.match(state)
    return match is not None and parse_date(match.group(1)) is not None


def state_kind(state: str) -> str:
    state = (state or "").strip()
    if state.startswith("已完成"):
        return "已完成"
    return state


def render_line(content: str, recorded: str, due: str, state: str, history: str) -> str:
    return (
        f"- 内容：{content} ｜ 记录日：{recorded} ｜ 到期日：{due} "
        f"｜ 状态：{state} ｜ 提醒历史：{history}"
    )


@dataclass
class Entry:
    line_no: int
    raw: str
    content: str = ""
    recorded: str = ""
    due: str = DUE_EMPTY
    state: str = ""
    history: str = ""
    valid: bool = False
    legacy: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class Ledger:
    path: Path
    lines: list[str]
    had_bom: bool = False
    newline: str = "\n"


def read_ledger(path: Path) -> Ledger:
    if not path.exists():
        return Ledger(path=path, lines=[])
    raw = path.read_bytes()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    return Ledger(path=path, lines=lines, had_bom=had_bom, newline=newline)


def write_ledger(ledger: Ledger, backup: bool = False) -> None:
    ledger.path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(ledger.lines)
    if text and not text.endswith(("\n", "\r")):
        text += ledger.newline
    data = text.encode("utf-8")
    if ledger.had_bom:
        data = b"\xef\xbb\xbf" + data

    if backup and ledger.path.exists():
        backup_path = ledger.path.with_name(ledger.path.name + ".bak")
        backup_path.write_bytes(ledger.path.read_bytes())

    tmp = ledger.path.with_name(f"{ledger.path.name}.tmp.{os.getpid()}")
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        last_error: Optional[Exception] = None
        for _ in range(10):
            try:
                os.replace(tmp, ledger.path)
                return
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.05)
        raise LedgerError(f"写入清单失败：{last_error}")
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


class LedgerLock:
    """跨进程独占锁。POSIX 用 flock，Windows 用 msvcrt。"""

    def __init__(self, path: Path, timeout: float = 10.0):
        self.path = path
        self.timeout = timeout
        self.handle = None

    def __enter__(self) -> "LedgerLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = open(self.path, "a+b")
        deadline = time.time() + self.timeout
        if os.name == "nt":
            import msvcrt

            if self.handle.tell() == 0:
                self.handle.write(b"\0")
                self.handle.flush()
            while True:
                try:
                    self.handle.seek(0)
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                    return self
                except OSError as exc:
                    if time.time() > deadline:
                        raise LedgerError(f"等待清单锁超时：{self.path}") from exc
                    time.sleep(0.05)
        else:
            import fcntl

            while True:
                try:
                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return self
                except OSError as exc:
                    if time.time() > deadline:
                        raise LedgerError(f"等待清单锁超时：{self.path}") from exc
                    time.sleep(0.05)

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


def parse_labeled(raw: str) -> Optional[dict[str, str]]:
    matches = list(LABEL_RE.finditer(raw))
    if len(matches) < 4:
        return None
    fields: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        value = raw[start:end].strip().strip("｜|").strip()
        fields[LABEL_ALIASES[match.group(1)]] = value
    return fields


def parse_table_row(raw: str) -> Optional[dict[str, str]]:
    stripped = raw.strip()
    if not stripped.startswith("|"):
        return None
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if len(cells) < 5:
        return None
    if all(set(cell) <= {"-", ":", " "} for cell in cells if cell):
        return None
    if cells[0] in ("内容", "Content") or cells[3] in ("状态", "State"):
        return None
    return dict(zip(LABELS, cells[:5]))


def parse_entry(line_no: int, raw: str) -> Optional[Entry]:
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("|") and "---" in stripped:
        return None
    if stripped.startswith("|"):
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 5 and (cells[0] in ("内容", "Content") or cells[3] in ("状态", "State")):
            return None
    fields = parse_labeled(raw) or parse_table_row(raw)
    if fields is None:
        if stripped.startswith(("-", "*", "|")) or "内容" in stripped:
            return Entry(line_no=line_no, raw=raw, legacy=True, errors=["无法解析为五字段"])
        return None

    entry = Entry(line_no=line_no, raw=raw)
    entry.content = fields.get("内容", "").strip()
    entry.recorded = fields.get("记录日", "").strip()
    entry.due = fields.get("到期日", "").strip() or DUE_EMPTY
    entry.state = fields.get("状态", "").strip()
    entry.history = fields.get("提醒历史", "").strip()

    if not entry.content:
        entry.errors.append("内容为空")
    if not entry.recorded:
        entry.errors.append("记录日为空")
    elif parse_date(entry.recorded) is None:
        entry.errors.append("记录日不是 YYYY-MM-DD")
    if entry.due not in ("", DUE_EMPTY) and parse_date(entry.due) is None:
        entry.errors.append("到期日不是 YYYY-MM-DD 或 —")
    if not state_is_valid(entry.state):
        entry.errors.append("状态不是五种之一")
    if not entry.history:
        entry.errors.append("提醒历史为空")
    entry.valid = not entry.errors
    return entry


def entries_of(ledger: Ledger) -> list[Entry]:
    entries: list[Entry] = []
    for line_no, raw in enumerate(ledger.lines, start=1):
        entry = parse_entry(line_no, raw)
        if entry is not None:
            entries.append(entry)
    return entries


def entry_dict(entry: Entry) -> dict:
    return {
        "line": entry.line_no,
        "content": entry.content,
        "recorded": entry.recorded,
        "due": entry.due,
        "state": entry.state,
        "history": entry.history,
        "valid": entry.valid,
        "legacy": entry.legacy,
        "errors": entry.errors,
    }


def sort_key(entry: Entry):
    due = parse_date(entry.due)
    return (due is None, due or date.max, entry.line_no)


def find_candidates(entries: list[Entry], match: Optional[str], line_no: Optional[int]) -> list[Entry]:
    if line_no is not None:
        return [entry for entry in entries if entry.line_no == line_no]
    if not match:
        raise LedgerError("需要 --match 或 --line 来定位条目", 2)
    needle = match.strip()
    return [
        entry
        for entry in entries
        if needle in entry.raw or needle in entry.content
    ]


def emit(data: dict, as_json: bool, human: str) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(human)


def cmd_add(args: argparse.Namespace) -> int:
    if not args.content.strip():
        raise LedgerError("内容不能为空")
    if args.waiting and args.followup:
        raise LedgerError("--waiting 与 --followup 只能选一个")
    state = args.state or (
        WAITING_STATE if args.waiting else "待跟进" if args.followup else "未完成"
    )
    if not state_is_valid(state):
        raise LedgerError(f"非法状态：{state}")
    due = normalize_due(args.due)
    recorded = normalize_due(args.recorded or today_str())
    if parse_date(recorded) is None:
        raise LedgerError(f"记录日必须是 YYYY-MM-DD，收到：{recorded}")
    history = args.history or DEFAULT_HISTORY
    line = render_line(args.content.strip(), recorded, due, state, history)

    path = Path(args.file).expanduser()
    with LedgerLock(path.with_name(path.name + ".lock")):
        ledger = read_ledger(path)
        if ledger.lines and not ledger.lines[-1].endswith(("\n", "\r")):
            ledger.lines[-1] += ledger.newline
        ledger.lines.append(line + ledger.newline)
        line_no = len(ledger.lines)
        write_ledger(ledger, backup=args.backup)

    entry = parse_entry(line_no, line)
    payload = {
        "path": str(path),
        "line": line,
        "entry": entry_dict(entry) if entry else None,
    }
    emit(payload, args.json, f"已追加：{line}\n清单：{path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser()
    ledger = read_ledger(path)
    entries = entries_of(ledger)
    if args.state:
        wanted = set(args.state)
        entries = [entry for entry in entries if state_kind(entry.state) in wanted]
    if args.open:
        entries = [entry for entry in entries if state_kind(entry.state) in OPEN_STATES | {WAITING_STATE}]
    if args.due_within is not None:
        horizon = date.today() + timedelta(days=args.due_within)
        entries = [
            entry
            for entry in entries
            if state_kind(entry.state) in OPEN_STATES | {WAITING_STATE}
            and parse_date(entry.due) is not None
            and parse_date(entry.due) <= horizon
        ]
    entries.sort(key=sort_key)

    if args.json:
        print(json.dumps({"path": str(path), "entries": [entry_dict(e) for e in entries]}, ensure_ascii=False, indent=2))
    else:
        if not entries:
            print("清单为空。")
        for entry in entries:
            mark = "" if entry.valid else "（格式待修）"
            print(f"[{entry.line_no}] {entry.state} ｜ {entry.content} ｜ 到期 {entry.due}{mark}")
    return 0


def due_note(entry: Entry, waiting: bool = False) -> str:
    parsed = parse_date(entry.due)
    if parsed is None:
        return "未定期限"
    if waiting and parsed <= date.today():
        return f"{entry.due}（该跟进）"
    return entry.due


def cmd_query(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser()
    ledger = read_ledger(path)
    entries = [entry for entry in entries_of(ledger) if entry.valid]
    todo = sorted(
        (entry for entry in entries if state_kind(entry.state) in OPEN_STATES),
        key=sort_key,
    )
    waiting = sorted(
        (entry for entry in entries if state_kind(entry.state) == WAITING_STATE),
        key=sort_key,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "path": str(path),
                    "sections": {
                        "todo": [entry_dict(entry) for entry in todo],
                        "waiting": [entry_dict(entry) for entry in waiting],
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print("你要做的：")
    if not todo:
        print("- （无）")
    for entry in todo:
        print(f"- [{entry.line_no}] {entry.content} ｜ 到期 {due_note(entry)}")
    print("等对方：")
    if not waiting:
        print("- （无）")
    for entry in waiting:
        print(f"- [{entry.line_no}] {entry.content} ｜ 到期 {due_note(entry, waiting=True)}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    changes = any(
        [
            args.complete,
            args.void,
            args.delete,
            args.state,
            args.due is not None,
            args.history is not None,
            args.append_history,
            args.content,
        ]
    )
    if not changes:
        raise LedgerError("没有指定要做的修改", 2)

    path = Path(args.file).expanduser()
    with LedgerLock(path.with_name(path.name + ".lock")):
        ledger = read_ledger(path)
        entries = entries_of(ledger)
        candidates = find_candidates(entries, args.match, args.line)
        if not candidates:
            raise LedgerError("没有找到匹配的条目", 2)
        if len(candidates) > 1:
            listing = "\n".join(
                f"  [{entry.line_no}] {entry.content}" for entry in candidates
            )
            raise LedgerError(f"匹配到多条，请用 --line 指定：\n{listing}", 3)
        entry = candidates[0]
        index = entry.line_no - 1

        if args.delete:
            del ledger.lines[index]
            write_ledger(ledger, backup=args.backup)
            emit(
                {"path": str(path), "deleted": entry.content},
                args.json,
                f"已删除：{entry.content}",
            )
            return 0

        if state_kind(entry.state) in ("已完成", "已作废"):
            raise LedgerError("已完成/已作废的条目只读；要移除只能整行删除", 2)
        if not entry.valid:
            raise LedgerError(f"该行无法安全改写（{'; '.join(entry.errors)}）：{entry.raw.strip()}")

        content = entry.content
        recorded = entry.recorded
        due = entry.due
        state = entry.state
        history = entry.history

        if args.content:
            content = args.content.strip()
        if args.complete:
            state = f"已完成 {today_str()}"
        if args.void:
            state = "已作废"
        if args.state:
            if not state_is_valid(args.state):
                raise LedgerError(f"非法状态：{args.state}")
            state = args.state
        if args.due is not None:
            new_due = normalize_due(args.due)
            if new_due != due:
                note = f"改期：原到期 {due}"
                history = f"{history}；{note}" if history else note
            due = new_due
        if args.history is not None:
            history = args.history.strip() or DEFAULT_HISTORY
        if args.append_history:
            history = f"{history}；{args.append_history.strip()}" if history else args.append_history.strip()

        new_line = render_line(content, recorded, due, state, history)
        ledger.lines[index] = new_line + ("\r\n" if ledger.newline == "\r\n" else "\n")
        write_ledger(ledger, backup=args.backup)

    new_entry = parse_entry(entry.line_no, new_line)
    payload = {
        "path": str(path),
        "line": new_line,
        "entry": entry_dict(new_entry) if new_entry else None,
    }
    emit(payload, args.json, f"已更新：{new_line}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser()
    ledger = read_ledger(path)
    entries = entries_of(ledger)
    issues: list[dict] = []
    seen: dict[tuple[str, str], int] = {}

    for entry in entries:
        if entry.legacy:
            issues.append({"line": entry.line_no, "issue": entry.errors[0], "raw": entry.raw.strip()})
            continue
        for error in entry.errors:
            issues.append({"line": entry.line_no, "issue": error, "raw": entry.raw.strip()})
        key = (entry.content, entry.due)
        if key in seen:
            issues.append(
                {
                    "line": entry.line_no,
                    "issue": f"与第 {seen[key]} 条内容与到期日重复",
                    "raw": entry.raw.strip(),
                }
            )
        else:
            seen[key] = entry.line_no

    payload = {
        "path": str(path),
        "entries": len(entries),
        "legacy": sum(1 for entry in entries if entry.legacy),
        "issues": issues,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"清单：{path}")
        print(f"条目：{len(entries)}（无法解析 {payload['legacy']}）")
        if issues:
            print(f"问题：{len(issues)}")
            for issue in issues:
                print(f"  第 {issue['line']} 行：{issue['issue']}")
        else:
            print("没有问题。")
    return 1 if issues else 0


def cmd_due(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser()
    ledger = read_ledger(path)
    entries = entries_of(ledger)
    today = date.today()
    horizon = today + timedelta(days=args.within)
    eligible: list[tuple[str, Entry, Optional[date]]] = []

    for entry in entries:
        if not entry.valid:
            continue
        kind = state_kind(entry.state)
        due = parse_date(entry.due)
        if due is None:
            continue
        if kind in OPEN_STATES and due <= horizon:
            eligible.append(("todo", entry, due))
        elif kind == WAITING_STATE and due <= today:
            eligible.append(("waiting", entry, due))

    eligible.sort(key=lambda item: (item[2] is None, item[2] or date.max, item[1].line_no))
    if args.json:
        print(
            json.dumps(
                {
                    "path": str(path),
                    "within": args.within,
                    "entries": [
                        {"kind": kind, **entry_dict(entry)} for kind, entry, _ in eligible
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        if not eligible:
            print("窗口内没有可提的条目。")
        for kind, entry, _ in eligible:
            label = "你要做的" if kind == "todo" else "等对方"
            print(f"[{label}] {entry.content} ｜ 到期 {entry.due} ｜ {entry.state}")
    return 0


def run_cli(ledger_path: Path, *args: str) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--file",
        str(ledger_path),
        *args,
    ]
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8")


def cmd_self_test(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="work-companion-selftest-") as tmp:
        ledger_path = Path(tmp) / "commitments.md"

        first = run_cli(ledger_path, "add", "--content", "周五交方案", "--due", "2026-11-20")
        assert first.returncode == 0, first.stderr
        second = run_cli(
            ledger_path,
            "add",
            "--content",
            "问他报价",
            "--followup",
            "--due",
            "2026-11-18",
        )
        assert second.returncode == 0, second.stderr

        listing = run_cli(ledger_path, "list", "--json")
        assert listing.returncode == 0, listing.stderr
        entries = json.loads(listing.stdout)["entries"]
        assert len(entries) == 2, entries
        assert entries[0]["state"] == "待跟进", entries[0]

        ambiguous = run_cli(ledger_path, "update", "--match", "方案", "--complete")
        assert ambiguous.returncode == 0, ambiguous.stderr
        done = run_cli(ledger_path, "update", "--match", "问他报价", "--complete")
        assert done.returncode == 0, done.stderr

        validation = run_cli(ledger_path, "validate")
        assert validation.returncode == 0, validation.stdout + validation.stderr

        due = run_cli(ledger_path, "due", "--within", "3", "--json")
        assert due.returncode == 0, due.stderr

        third = run_cli(ledger_path, "add", "--content", "重复条目", "--due", "2026-12-01")
        fourth = run_cli(ledger_path, "add", "--content", "重复条目", "--due", "2026-12-01")
        assert third.returncode == 0 and fourth.returncode == 0
        ambiguous = run_cli(ledger_path, "update", "--match", "重复条目", "--void")
        assert ambiguous.returncode == 3, ambiguous.stderr

        delete = run_cli(ledger_path, "update", "--match", "重复条目", "--line", "3", "--delete")
        assert delete.returncode == 0, delete.stderr

        # 并发追加：两个进程同时写，锁保证两条都在。
        concurrent_path = Path(tmp) / "concurrent.md"
        procs = [
            subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--file",
                    str(concurrent_path),
                    "add",
                    "--content",
                    f"并发条目 {index}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            for index in (1, 2)
        ]
        for proc in procs:
            proc.communicate(timeout=30)
            assert proc.returncode == 0
        concurrent_list = run_cli(concurrent_path, "list", "--json")
        assert len(json.loads(concurrent_list.stdout)["entries"]) == 2

    print("self-test ok")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="work-companion 可选清单工具：安全读写、校验与到期筛选。",
    )
    parser.add_argument(
        "--file",
        default=str(DEFAULT_LEDGER),
        help=f"清单路径（默认 {DEFAULT_LEDGER}）",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add", help="追加一条记录")
    add.add_argument("--content", required=True, help="用户原话")
    add.add_argument("--due", default=DUE_EMPTY, help="到期日 YYYY-MM-DD、today、+N 或 —")
    add.add_argument("--recorded", default=None, help="记录日，默认今天")
    add.add_argument("--state", default=None, help="五种状态之一")
    add.add_argument("--history", default=None, help="提醒历史，默认“未提”")
    add.add_argument("--waiting", action="store_true", help="记为等待对方")
    add.add_argument("--followup", action="store_true", help="记为待跟进")
    add.add_argument("--backup", action="store_true", help="写入前保留 .bak")
    add.add_argument("--json", action="store_true", help="输出 JSON")
    add.set_defaults(func=cmd_add)

    query = subparsers.add_parser("query", help="按“你要做的/等对方”两段列出未结项")
    query.add_argument("--json", action="store_true", help="输出 JSON")
    query.set_defaults(func=cmd_query)

    listing = subparsers.add_parser("list", help="列出记录")
    listing.add_argument("--state", action="append", choices=sorted(STATES), help="按状态筛选，可重复")
    listing.add_argument("--open", action="store_true", help="只列未结项：未完成/待跟进/等待对方")
    listing.add_argument("--due-within", type=int, default=None, help="只列 N 天内到期的")
    listing.add_argument("--json", action="store_true", help="输出 JSON")
    listing.set_defaults(func=cmd_list)

    update = subparsers.add_parser("update", help="更新或删除一条记录")
    update.add_argument("--match", default=None, help="用原话片段定位")
    update.add_argument("--line", type=int, default=None, help="用行号定位（行号见 list 输出）")
    update.add_argument("--content", default=None, help="替换内容")
    update.add_argument("--due", default=None, help="改到期日")
    update.add_argument("--state", default=None, help="改状态（五种之一）")
    update.add_argument("--complete", action="store_true", help="标记已完成并附今天日期")
    update.add_argument("--void", action="store_true", help="标记已作废")
    update.add_argument("--delete", action="store_true", help="整行删除")
    update.add_argument("--history", default=None, help="替换提醒历史")
    update.add_argument("--append-history", default=None, help="追加提醒历史")
    update.add_argument("--backup", action="store_true", help="写入前保留 .bak")
    update.add_argument("--json", action="store_true", help="输出 JSON")
    update.set_defaults(func=cmd_update)

    validate = subparsers.add_parser("validate", help="校验五字段与状态")
    validate.add_argument("--json", action="store_true", help="输出 JSON")
    validate.set_defaults(func=cmd_validate)

    due = subparsers.add_parser("due", help="列出收尾窗口内可提的条目")
    due.add_argument("--within", type=int, default=3, help="未完成/待跟进的天数窗口，默认 3")
    due.add_argument("--json", action="store_true", help="输出 JSON")
    due.set_defaults(func=cmd_due)

    self_test = subparsers.add_parser("self-test", help="在临时目录跑一轮读写与并发自测")
    self_test.set_defaults(func=cmd_self_test)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except LedgerError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
