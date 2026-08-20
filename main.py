#!/usr/bin/env python3
"""Instagram Multi-Tool - CLI entry point.

Usage:
  python main.py              interactive menu
  python main.py --chat       jump straight to AI chat
"""

import sys

import banner
import config as config_mod
from actions import DIM, ERR, RESET, WARN, login

try:
    import instagrapi
except ImportError:
    instagrapi = None


def client_factory():
    return instagrapi.Client()  # pyright: ignore[reportOptionalMemberAccess]


def show_banner():
    print(banner.render())


def menu() -> str:
    print("\n  [1] AI chat")
    print("  [2] Mass unfollow")
    print("  [3] Remove followers")
    print("  [4] Leave group chat")
    print("  [5] Quit")
    return input(f"{WARN}choose:{RESET} ").strip()


def ensure_deps():
    if instagrapi is None:
        print(f"{ERR}instagrapi not installed. Run: pip install -r requirements.txt{RESET}")
        return False
    return True


def main():
    show_banner()
    cfg = config_mod.load_config()
    if config_mod.first_run():
        print(
            f"{DIM}first run: copy config.example.json to config.json "
            f"and fill in your username/password/RESET"
        )

    client = None
    if ensure_deps():
        client = login(client_factory, cfg)

    if client is None:
        print(f"{ERR}no client - cannot continue.{RESET}")
        sys.exit(1)

    jump_chat = len(sys.argv) > 1 and sys.argv[1] == "--chat"
    try:
        while True:
            if jump_chat:
                choice = "1"
                jump_chat = False
            else:
                choice = menu()
            if choice == "1":
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
            elif choice == "5":
                print("bye.")
                break
            else:
                print(f"{ERR}unknown option{RESET}")
    except KeyboardInterrupt:
        print(f"\n{WARN}interrupted.{RESET}")


if __name__ == "__main__":
    main()