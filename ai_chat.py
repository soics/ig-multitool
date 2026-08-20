"""AI chat tool.

Talks to an OpenAI-compatible chat endpoint (any gateway that speaks
/v1/chat/completions, e.g. a local 9router). Supports a whitelist mode:
only whitelisted users can DM the account, everyone else's messages are
ignored. Whitelist lives in config.json and can be managed here.
"""

import json
import time
import urllib.request

from colorama import Fore, Style

from actions import RESET, WARN, confirm, printable, Config  # pyright: ignore[reportImplicitRelativeImport]

WHITELISTED = "whitelisted"
EVERYONE = "everyone"

DIM = Style.DIM


def _get_recent_messages(client, limit: int = 10):
    try:
        return client.direct_threads(amount=limit)
    except Exception:
        try:
            return client.direct_threads()[:limit]
        except Exception:
            return []


def _pending_threads(client, limit: int = 10):
    threads = _get_recent_messages(client, limit)
    pending = []
    for thread in threads:
        try:
            if getattr(thread, "pending", False):
                pending.append(thread)
        except Exception:
            continue
    return pending


def ai_reply(cfg: Config, prompt: str) -> str | None:
    ai = cfg.get("ai", {})
    if not ai.get("enabled") or not ai.get("api_key"):
        return None
    body = {
        "model": ai.get("model", "ollama/gpt-oss:120b"),
        "messages": [
            {"role": "system", "content": ai.get("system_prompt", "")},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 500,
    }
    req = urllib.request.Request(
        ai["base_url"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ai['api_key']}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001
        print(f"{Fore.RED}AI request failed: {exc}{RESET}")
        return None


def _whitelist_menu(cfg: Config) -> None:
    while True:
        wl = cfg.get("whitelist", [])
        print(f"\n{DIM}whitelist ({len(wl)}): {', '.join(wl) or 'empty'}{RESET}")
        print("  1) add user")
        print("  2) remove user")
        print("  3) back")
        choice = input(f"{WARN}choose:{RESET} ").strip()
        if choice == "1":
            name = input("username: ").strip().lstrip("@")
            if name and name not in wl:
                cfg.setdefault("whitelist", []).append(name)
                print(f"{Fore.GREEN}added {name}{RESET}")
        elif choice == "2":
            name = input("username: ").strip().lstrip("@")
            if name in wl:
                wl.remove(name)
                print(f"{Fore.GREEN}removed {name}{RESET}")
        elif choice == "3":
            break


def chat_loop(client, cfg: Config) -> None:
    """Main AI chat loop: reads recent DMs, replies with AI or canned text."""
    print("AI chat mode. Press Ctrl+C to exit.")
    print(f"{DIM}ai.enabled = {cfg['ai'].get('enabled')}{RESET}")
    print(f"{DIM}whitelist mode = {WHITELISTED if cfg['ai'].get('enabled') else 'n/a'}{RESET}")
    last_replied = {}

    while True:
        try:
            threads = _get_recent_messages(client, limit=10)
        except KeyboardInterrupt:
            print("\nbye.")
            return
        for thread in threads:
            try:
                username = printable(thread)
                if not username:
                    continue
                if cfg["ai"].get("enabled") and cfg.get("whitelist") and username not in cfg["whitelist"]:
                    continue
                now = time.time()
                if last_replied.get(username, 0) + 60 > now:
                    continue
                last_replied[username] = now
                prompt = f"user @{username} wrote: {thread}"
                reply = ai_reply(cfg, prompt)
                if not reply:
                    reply = f"hey @{username}, I'll get back to you shortly."
                print(f"{DIM}-> {username}: {reply[:120]}{RESET}")
            except Exception as exc:  # noqa: BLE001
                print(f"{Fore.RED}skip thread: {exc}{RESET}")
        time.sleep(20)


def run(client, cfg: Config) -> None:
    print("AI chat with whitelist control")
    while True:
        print("\n  1) chat (reply to DMs automatically)")
        print("  2) whitelist management")
        print("  3) back")
        choice = input(f"{WARN}choose:{RESET} ").strip()
        if choice == "1":
            chat_loop(client, cfg)
        elif choice == "2":
            _whitelist_menu(cfg)
        elif choice == "3":
            return
