"""
Splash banner for IG Multi Tool.

"IG" and "MULTI TOOL" rendered in a heavy block figlet font (banner3),
stacked and centered. White text with red accent on the dense glyphs,
animated line-by-line reveal + glyph shimmer.

Cross-platform: falls back to a slim banner when pyfiglet is missing
or the terminal is too narrow. Uses ui.py helpers so ANSI/UTF-8 are
handled safely on Windows, macOS, and Linux.
"""

import sys
import time

try:
    import pyfiglet  # type: ignore[import-not-found]

    _has_pyfiglet = True
except ImportError:
    _has_pyfiglet = False

import ui
from ui import BRIGHT, CYAN, DIM, RED, RESET, WHITE

HAS_DEPS = _has_pyfiglet

TOP_TEXT = "IG"
BOTTOM_TEXT = "MULTI TOOL"
SUBTITLE = "made by soics"

TOP_FONT_CANDIDATES = ["banner3", "doom", "colossal", "univers"]
BOTTOM_FONT_CANDIDATES = ["banner3", "3-d", "cyberlarge", "soft"]

LIGHT_CHARS = set(":.'`,-_")
DENSE_CHARS = set("#%@&$")

ACCENT_CYCLE = [RED, CYAN, RED, WHITE]


def _shade_line(line: str) -> str:
    out = []
    for ch in line:
        if ch == " ":
            out.append(ch)
        elif ch in LIGHT_CHARS:
            out.append(f"{WHITE}{DIM}{ch}{RESET}")
        elif ch in DENSE_CHARS:
            out.append(f"{RED}{BRIGHT}{ch}{RESET}")
        else:
            out.append(f"{WHITE}{ch}{RESET}")
    return "".join(out)


def _render_with_candidates(text: str, candidates: list[str]):
    if not HAS_DEPS:
        return None
    for name in candidates:
        try:
            fig = pyfiglet.Figlet(font=name)  # type: ignore[name-defined]
            rendered = fig.renderText(text).rstrip("\n")
            lines = [l.rstrip() for l in rendered.split("\n")]
            while lines and not lines[-1].strip():
                lines.pop()
            return lines
        except Exception:
            continue
    return None


def _banner_lines(width: int) -> list[str] | None:
    top_lines = _render_with_candidates(TOP_TEXT, TOP_FONT_CANDIDATES)
    bottom_lines = _render_with_candidates(BOTTOM_TEXT, BOTTOM_FONT_CANDIDATES)

    if top_lines is None or bottom_lines is None:
        fallback = _render_with_candidates(
            f"{TOP_TEXT} {BOTTOM_TEXT}", ["ansi_shadow", "big", "standard"]
        )
        if fallback is None:
            return None
        top_lines, bottom_lines = fallback, []

    all_lines = top_lines + bottom_lines
    if not all_lines:
        return None
    if max(len(l) for l in all_lines) > width:
        return None
    if max(len(l) for l in all_lines) * 2 + 4 <= width:
        all_lines = _double_width(all_lines)
    return all_lines


def _double_width(lines: list[str]) -> list[str]:
    return ["".join(ch * 2 for ch in line) for line in lines]


def _slim_lines(width: int) -> list[str] | None:
    if HAS_DEPS:
        try:
            fig = pyfiglet.Figlet(font="slant")  # type: ignore[name-defined]
            rendered = fig.renderText(f"{TOP_TEXT} {BOTTOM_TEXT}").rstrip("\n")
            lines = [l.rstrip() for l in rendered.split("\n")]
            if max(len(l) for l in lines) <= width:
                if max(len(l) for l in lines) * 2 + 4 <= width:
                    lines = _double_width(lines)
                return lines
        except Exception:
            pass
    return [f"== {TOP_TEXT} {BOTTOM_TEXT} =="]


def _subtitle(width: int | None = None) -> str:
    text = SUBTITLE if width is None else _center(SUBTITLE, width)
    if ui.HAS_COLOR:
        return f"{RED}{BRIGHT}{text}{RESET}"
    return text


def _center(line: str, width: int) -> str:
    pad = max((width - len(line)) // 2, 0)
    return " " * pad + line


def _lines_for(width: int):
    return _banner_lines(width) or _slim_lines(width) or [f"== {TOP_TEXT} {BOTTOM_TEXT} =="]


def render() -> str:
    """Static banner, no animation (useful for non-TTY output)."""
    import shutil

    width = shutil.get_terminal_size(fallback=(80, 24)).columns
    lines = _lines_for(width)
    body = "\n".join(_shade_line(_center(l, width)) for l in lines)
    return f"{body}\n{_subtitle(width)}\n"


def _shimmer_positions(lines: list[str], width: int) -> list[tuple[int, int, int]]:
    positions = []
    for y, line in enumerate(lines):
        pad = max((width - len(line)) // 2, 0)
        for x, ch in enumerate(line):
            if ch in DENSE_CHARS:
                positions.append((y, x, x + pad))
    return positions


def print_animated(speed: float = 0.012) -> None:
    """Type the banner line by line, then shimmer accent glyphs."""
    import shutil

    width = shutil.get_terminal_size(fallback=(80, 24)).columns
    lines = _lines_for(width)

    # line-by-line reveal
    for line in lines:
        print(_shade_line(_center(line, width)))
        sys.stdout.flush()
        time.sleep(speed)

    # shimmer: recolor dense glyphs through an accent cycle
    positions = _shimmer_positions(lines, width)
    if positions and ui.supports_cursor():
        for i in range(len(ACCENT_CYCLE) * 2):
            for y, x, col in positions:
                color = ACCENT_CYCLE[i % len(ACCENT_CYCLE)]
                print(
                    f"\033[{y + 1};{col + 1}H{color}{BRIGHT}{lines[y][x]}{RESET}",
                    end="",
                )
            sys.stdout.flush()
            time.sleep(0.08)
        print(f"\033[{len(lines) + 1};1H", end="")
        sys.stdout.flush()
        time.sleep(0.15)
    else:
        time.sleep(0.2)

    print(f"{_subtitle(width)}\n")


if __name__ == "__main__":
    print_animated()