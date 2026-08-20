"""Cross-platform UI kit: panels, menus, headers, spinners.

Works on Windows (legacy cmd + Windows Terminal), macOS, and Linux.
- `ensure_utf8()` makes stdout UTF-8-safe everywhere it can be.
- `unicode_ok()` detects whether box-drawing characters are safe; the
  kit falls back to ASCII borders when they are not.
- `colorama.init()` is called here so ANSI colors + cursor movement
  work on Windows 10+ consoles.
"""

import re
import sys
import time
from pathlib import Path
from typing import Any

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _visible_len(text: str) -> int:
    return len(_ANSI_RE.sub("", text))

try:
    import colorama

    colorama.init()
    _fore_mod: Any = colorama.Fore
    _style_mod: Any = colorama.Style
    _has_color = True
except ImportError:
    _fore_mod: Any = None
    _style_mod: Any = None
    _has_color = False

BASE_DIR = Path(__file__).resolve().parent
HAS_COLOR = _has_color


def _color(name: str) -> str:
    if not HAS_COLOR or _fore_mod is None:
        return ""
    return getattr(_fore_mod, name, "")


def _style(name: str) -> str:
    if not HAS_COLOR or _style_mod is None:
        return ""
    return getattr(_style_mod, name, "")


WHITE = _color("WHITE")
RED = _color("RED")
GREEN = _color("GREEN")
YELLOW = _color("YELLOW")
CYAN = _color("CYAN")
MAGENTA = _color("MAGENTA")
DIM = _style("DIM")
BRIGHT = _style("BRIGHT")
RESET = _style("RESET_ALL")


def ensure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure is not None:
                reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def unicode_ok() -> bool:
    if not HAS_COLOR:
        return False
    enc = (getattr(sys.stdout, "encoding", "") or "").lower()
    return "utf" in enc or "cp65001" in enc


def _enable_windows_vt() -> bool:
    """Enable ANSI VT processing on the Windows console (Win10+).

    Returns True only when raw cursor-escape sequences will actually be
    interpreted. On legacy consoles (or when the call fails) the caller
    must not emit them - colorama only converts color codes, not cursor
    movement.
    """
    if sys.platform != "win32":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        if not (mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING):
            if not kernel32.SetConsoleMode(
                handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            ):
                return False
        return True
    except Exception:  # noqa: BLE001 - non-Windows or restricted env
        return False


def supports_cursor() -> bool:
    if not HAS_COLOR:
        return False
    if not sys.stdout.isatty():
        return False
    return _enable_windows_vt()


def _terminal_width() -> int:
    try:
        import shutil

        return shutil.get_terminal_size(fallback=(80, 24)).columns
    except Exception:
        return 80


def hbar(title: str = "", width: int | None = None) -> str:
    if width is None:
        width = _terminal_width()
    inner = max(width - 2, 4)
    if title:
        text = f" {title} "
        if len(text) > inner:
            text = text[: inner - 1] + "…"
        pad = inner - len(text)
        left = pad // 2
        right = pad - left
        body = "─" * left + text + "─" * right
    else:
        body = "─" * inner
    if unicode_ok():
        return f"{DIM}┌{body}┐{RESET}"
    return f"{DIM}+{'-' * inner}+{RESET}"


def header(title: str, subtitle: str = "") -> None:
    print()
    print(hbar(title.upper()))
    if subtitle:
        print(f"  {DIM}{subtitle}{RESET}")
    print()


def footer(text: str = "") -> None:
    print(hbar(text))


def box(title: str, lines: list[str]) -> None:
    unicode_ = unicode_ok()
    tl, tr, bl, br = ("┌", "┐", "└", "┘") if unicode_ else ("+", "+", "+", "+")
    hz, vt = ("─", "│") if unicode_ else ("-", "|")
    max_visible = max(_visible_len(l) for l in lines) if lines else 0
    min_width = min(60, _terminal_width() - 2)
    width = min(max(max_visible + 4, _visible_len(title) + 4, min_width), _terminal_width() - 2)
    top = f"{DIM}{tl}{hz}{RESET} {BRIGHT}{title}{RESET} {DIM}{hz * (width - _visible_len(title) - 3)}{tr}{RESET}"
    print(top)
    for line in lines:
        pad = max(width - _visible_len(line), 0)
        print(f"{DIM}{vt}{RESET} {line}{' ' * pad} {DIM}{vt}{RESET}")
    print(f"{DIM}{bl}{hz * (width + 2)}{br}{RESET}")


def prompt(text: str, default: str = "") -> str:
    try:
        return input(f"{YELLOW}{text}{RESET} ").strip() or default
    except (EOFError, KeyboardInterrupt):
        print()
        return default


def menu(title: str, options: list[tuple[str, str]], prompt: str = "choose") -> str:
    lines = []
    for key, label in options:
        lines.append(f"{CYAN}{BRIGHT}{key}{RESET}  {WHITE}{label}{RESET}")
    lines.append("")
    lines.append(f"{DIM}ctrl+c to go back{RESET}")
    box(title, lines)
    try:
        return input(f"\n{YELLOW}{prompt} > {RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def status(ok: bool, text: str) -> None:
    if unicode_ok():
        mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    else:
        mark = f"{GREEN}ok{RESET}" if ok else f"{RED}!!{RESET}"
    print(f"  {mark} {text}")


def line(text: str, color: str = "") -> None:
    print(f"  {color}{text}{RESET}")


class Spinner:
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    ASCII_FRAMES = ["|", "/", "-", "\\"]

    def __init__(self, label: str = ""):
        self.label = label
        self._frames = self.FRAMES if unicode_ok() else self.ASCII_FRAMES
        self._running = False

    def __enter__(self):
        self._running = True
        return self

    def __exit__(self, *exc: Any) -> None:
        self.stop()

    def tick(self) -> None:
        if not sys.stdout.isatty():
            return
        for frame in self._frames:
            print(f"\r  {CYAN}{frame}{RESET} {self.label}", end="", flush=True)
            time.sleep(0.08)

    def stop(self, final: str = "") -> None:
        self._running = False
        clear = " " * (len(self.label) + 6)
        print(f"\r{clear}\r", end="", flush=True)
        if final:
            print(f"  {final}")


def spin(label: str, fn, *args: Any, **kwargs: Any):
    spinner = Spinner(label)
    spinner.tick()
    try:
        return fn(*args, **kwargs)
    finally:
        spinner.stop()