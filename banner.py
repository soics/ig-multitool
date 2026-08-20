"""
Splash banner for Instagram Multi-Tool.

Two-font mix: "INSTAGRAM" rendered in a geometric/colon-style figlet
font, "MULTI-TOOL" rendered in a curvy S-style figlet font, stacked
as one banner. Shaded gray-to-white for depth, matching the
black/white/red terminal theme (red is reserved for the subtitle and
any accent text).

Fallback: a slim, single-color font used when the terminal is too
narrow for the big banner, or when pyfiglet isn't installed.

Requires: pip install pyfiglet colorama
(Both are pure-Python, no network needed at runtime once installed.)

NOTE: font names below are best-guess matches for the two reference
styles. pyfiglet's bundled font set varies by version/install, so each
is tried in order and the first one that loads wins. Run
`python3 -c "import pyfiglet; print(pyfiglet.FigletFont.getFonts())"`
locally to see what's actually available and reorder the candidate
lists if the match isn't right.
"""

import shutil

try:
    import pyfiglet
    from colorama import init, Fore, Style
    init()
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

TOP_TEXT = "INSTAGRAM"
BOTTOM_TEXT = "MULTI-TOOL"
SUBTITLE = "made by soics"

# best-guess candidates, tried in order, first available wins
TOP_FONT_CANDIDATES = ["doom", "colossal", "computer", "univers"]
BOTTOM_FONT_CANDIDATES = ["soft", "3-d", "cyberlarge", "isometric1"]

# character "darkness" ramp, used to shade any font consistently
# instead of matching exact glyph characters per font
LIGHT_CHARS = set(":.'`,-_")      # thin/edge strokes -> dim (shadow)
DENSE_CHARS = set("#%@&$")        # heavy fill strokes -> bright (highlight)
# everything else (letters used as fill, +, ~, etc.) -> normal white


def _shade_line(line: str) -> str:
    out = []
    for ch in line:
        if ch == " ":
            out.append(ch)
        elif ch in LIGHT_CHARS:
            out.append(f"{Fore.WHITE}{Style.DIM}{ch}{Style.RESET_ALL}")
        elif ch in DENSE_CHARS:
            out.append(f"{Fore.WHITE}{Style.BRIGHT}{ch}{Style.RESET_ALL}")
        else:
            out.append(f"{Fore.WHITE}{ch}{Style.RESET_ALL}")
    return "".join(out)


def _render_with_candidates(text: str, candidates: list[str]):
    """Try each font name in order, return rendered lines from the
    first one that loads, or None if none are available."""
    if not HAS_DEPS:
        return None
    for name in candidates:
        try:
            fig = pyfiglet.Figlet(font=name)
            rendered = fig.renderText(text).rstrip("\n")
            return rendered.split("\n")
        except Exception:
            continue
    return None


def _big_banner(width: int) -> str | None:
    top_lines = _render_with_candidates(TOP_TEXT, TOP_FONT_CANDIDATES)
    bottom_lines = _render_with_candidates(BOTTOM_TEXT, BOTTOM_FONT_CANDIDATES)

    # if either half failed to load, fall back to a single known-good
    # font for the full text rather than a broken half-mix
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

    return "\n".join(_shade_line(l) for l in all_lines)


def _slim_banner(width: int) -> str:
    """Slim single-color fallback banner — used on narrow terminals or
    when pyfiglet isn't installed."""
    if HAS_DEPS:
        try:
            fig = pyfiglet.Figlet(font="slant")
            rendered = fig.renderText(f"{TOP_TEXT} {BOTTOM_TEXT}").rstrip("\n")
            lines = rendered.split("\n")
            if max(len(l) for l in lines) <= width:
                color = Fore.WHITE + Style.DIM
                return "\n".join(f"{color}{l}{Style.RESET_ALL}" for l in lines)
        except Exception:
            pass
    return f"== {TOP_TEXT} {BOTTOM_TEXT} =="


def render() -> str:
    """Return the full splash: banner + subtitle, sized to the terminal."""
    width = shutil.get_terminal_size(fallback=(80, 24)).columns
    banner = _big_banner(width) or _slim_banner(width)

    if HAS_DEPS:
        sub = f"{Fore.RED}{Style.DIM}{SUBTITLE}{Style.RESET_ALL}"
    else:
        sub = SUBTITLE

    return f"{banner}\n{sub}\n"


if __name__ == "__main__":
    print(render())
