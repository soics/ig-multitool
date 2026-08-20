"""Shared helpers: pacing, confirmation, progress tracking, session login.

All bulk actions sleep a random delay between actions (configurable via
pacing in config.json) and pause briefly after every batch so the
account doesn't look automated. Ctrl+C anywhere aborts cleanly and
prints how far the run got.
"""

import os
import random
import time
from typing import Any

from colorama import Fore, Style

Config = dict[str, Any]

WARN = Fore.YELLOW
ERR = Fore.RED
DIM = Style.DIM
RESET = Style.RESET_ALL


class AbortedError(Exception):
    """Raised when the user presses Ctrl+C mid-run."""


def human_count(n: int) -> str:
    return f"{n} {Fore.CYAN}{'account' if n == 1 else 'accounts'}{RESET}"


def confirm(question: str, default_no: bool = False) -> bool:
    hint = "y/N" if default_no else "Y/n"
    while True:
        try:
            answer = input(f"{WARN}{question} [{hint}]{RESET} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            raise AbortedError("cancelled by user")
        if not answer:
            return not default_no
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print(f"{ERR}Please answer y or n.{RESET}")


def pick_number(prompt: str, minimum: int = 1, maximum: int | None = None) -> int:
    while True:
        try:
            raw = input(f"{WARN}{prompt}{RESET} ").strip()
            value = int(raw)
        except (EOFError, KeyboardInterrupt):
            print()
            raise AbortedError("cancelled by user")
        except ValueError:
            print(f"{ERR}Enter a number.{RESET}")
            continue
        if value < minimum or (maximum is not None and value > maximum):
            print(f"{ERR}Enter a number between {minimum} and {maximum}.{RESET}")
            continue
        return value


def sleep_between_actions(cfg: Config) -> None:
    pacing = cfg.get("pacing", {})
    low = float(pacing.get("action_delay_min", 3))
    high = float(pacing.get("action_delay_max", 15))
    if high < low:
        low, high = high, low
    delay = random.uniform(low, high)
    try:
        time.sleep(delay)
    except KeyboardInterrupt:
        raise AbortedError("cancelled during delay")


def maybe_batch_pause(cfg: Config, done: int) -> None:
    pacing = cfg.get("pacing", {})
    every = int(pacing.get("batch_pause_every", 10))
    seconds = int(pacing.get("batch_pause_seconds", 60))
    if every <= 0 or seconds <= 0:
        return
    if done > 0 and done % every == 0:
        print(f"{DIM}pausing {seconds}s after {done} actions (batch pause)...{RESET}")
        try:
            time.sleep(seconds)
        except KeyboardInterrupt:
            raise AbortedError("cancelled during batch pause")


def read_done_file(path: str) -> set[str]:
    if not path:
        return set()
    try:
        with open(path, encoding="utf-8") as fh:
            return {line.strip() for line in fh if line.strip()}
    except FileNotFoundError:
        return set()


def append_done(path: str, handle: str) -> None:
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(handle + "\n")


def login(client_factory, cfg: Config):
    """Login with session reuse. Returns an instagrapi client or None.

    A saved session is loaded and verified with a lightweight
    account_info() call; a full username/password login only happens
    when there is no session or the session is rejected.
    """
    session_path = cfg.get("session_path") or "session.json"
    if os.path.exists(session_path):
        print("loading saved session...")
        client = client_factory()
        try:
            client.load_settings(session_path)
            client.account_info()
            return client
        except Exception as exc:  # noqa: BLE001 - session may be stale
            print(f"{DIM}session invalid ({exc}), logging in fresh...{RESET}")

    username = cfg.get("username") or ""
    password = cfg.get("password") or ""
    if not username or not password:
        username = input("Instagram username: ").strip()
        password = input("Instagram password: ").strip()
    print("logging in...")
    client = client_factory()
    client.login(username, password)
    try:
        client.dump_settings(session_path)
        print(f"session saved to {session_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"{WARN}could not save session: {exc}{RESET}")
    return client
