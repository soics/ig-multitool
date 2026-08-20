#!/usr/bin/env python3
"""IG Multi Tool - CLI entry point.

Cross-platform (Linux / macOS / Windows).

Usage:
  python main.py               interactive menu
  python main.py --chat        jump straight to AI chat
  python main.py --preview     browse the UI with fake data (no login)
"""

import sys

import banner
import config as config_mod
import ui
from actions import AbortedError
from ui import DIM, RED, RESET, YELLOW

try:
    import instagrapi  # type: ignore[import-not-found]

    _has_instagrapi = True
except ImportError:
    _has_instagrapi = False

WARN = YELLOW


def client_factory():
    return instagrapi.Client()  # type: ignore[attr-defined]


def fake_client_factory():
    from fake_client import FakeClient

    return FakeClient()


def show_banner():
    banner.print_animated()


def ensure_deps() -> bool:
    if not _has_instagrapi:
        print(f"{RED}instagrapi not installed. Run: pip install -r requirements.txt{RESET}")
        return False
    return True


def main_menu() -> str:
    return ui.menu(
        "IG MULTI TOOL",
        [
            ("1", "AI chat          - auto-reply to DMs (whitelist control)"),
            ("2", "Mass unfollow    - clean up your following list"),
            ("3", "Remove followers - prune who follows you"),
            ("4", "Leave group chat - exit one or several group threads"),
        ],
        prompt="select",
    )


def main():
    ui.ensure_utf8()
    show_banner()

    args = sys.argv[1:]
    preview = "--preview" in args
    jump_chat = "--chat" in args

    cfg = config_mod.load_config()
    if preview:
        print(f"{DIM}preview mode: fake data, no login, fast pacing.{RESET}")
        cfg.setdefault("pacing", {}).update(
            {"action_delay_min": 0.1, "action_delay_max": 0.2, "batch_pause_every": 0, "batch_pause_seconds": 0}
        )
        client = fake_client_factory()
    elif config_mod.first_run():
        print(
            f"{DIM}first run: copy config.example.json to config.json "
            f"and fill in your username/password{RESET}"
        )
        client = None
    else:
        from actions import login

        client = login(client_factory, cfg) if ensure_deps() else None

    if client is None:
        print(f"{RED}no client - cannot continue.{RESET}")
        sys.exit(1)

    jump_chat_first = jump_chat
    try:
        while True:
            if jump_chat_first:
                choice = "1"
                jump_chat_first = False
            else:
                choice = main_menu()
            if choice == "":
                print("bye.")
                break
            elif choice == "1":
                import ai_chat

                ai_chat.run(client, cfg)
            elif choice == "2":
                import mass_unfollow

                mass_unfollow.run(client, cfg)
            elif choice == "3":
                import remove_followers

                remove_followers.run(client, cfg)
            elif choice == "4":
                import leave_chat

                leave_chat.run(client, cfg)
            else:
                print(f"{RED}unknown option: {choice}{RESET}")
    except KeyboardInterrupt:
        print(f"\n{YELLOW}interrupted.{RESET}")
    except AbortedError:
        print(f"\n{YELLOW}interrupted.{RESET}")


if __name__ == "__main__":
    main()