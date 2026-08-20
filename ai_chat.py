"""AI chat tool.

Talks to an OpenAI-compatible chat endpoint (any gateway that speaks
/v1/chat/completions, e.g. a local 9router) and sends replies back into
the direct-message thread via instagrapi. Supports a whitelist mode
(ai.whitelist_only): only whitelisted users can DM the account, everyone
else's messages are ignored. Whitelist lives in config.json and can be
managed here.

Only genuinely new incoming messages are answered: each thread's last
answered message id is remembered, so a thread is never re-replied on
every poll. Own messages and messages without text (media, likes) are
never answered.
"""

import json
import time
import urllib.request

from actions import RESET, Config
from ui import CYAN, DIM, GREEN, RED, box, header, prompt

WHITELISTED = "whitelisted"
EVERYONE = "everyone"


def _get_recent_messages(client, limit: int = 10):
    try:
        return client.direct_threads(amount=limit)
    except Exception:  # noqa: BLE001
        try:
            return client.direct_threads()[:limit]
        except Exception:  # noqa: BLE001
            return []


def _resolve_sender(client, thread, msg):
    """Sender of a message: prefer the message's user_id, fall back to
    the first thread participant that is not the logged-in account."""
    msg_uid = str(getattr(msg, "user_id", "") or "")
    for user in getattr(thread, "users", []) or []:
        if msg_uid and str(getattr(user, "pk", "")) == msg_uid:
            return user
    self_pk = str(getattr(client, "user_id", ""))
    for user in getattr(thread, "users", []) or []:
        if str(getattr(user, "pk", "")) != self_pk:
            return user
    return None


def _newest_incoming(thread):
    """Newest message with text that was not sent by the account itself."""
    best = None
    best_ts = None
    for msg in getattr(thread, "messages", None) or []:
        if not getattr(msg, "text", None) or getattr(msg, "is_sent_by_viewer", False):
            continue
        msg_ts = getattr(msg, "timestamp", None)
        if best is None or (msg_ts is not None and (best_ts is None or msg_ts >= best_ts)):
            best = msg
            best_ts = msg_ts
    return best


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def ai_reply(cfg: Config, prompt_text: str) -> str | None:
    ai = cfg.get("ai", {})
    if not ai.get("enabled") or not ai.get("api_key"):
        return None
    body = {
        "model": ai.get("model", "ollama/gpt-oss:120b"),
        "messages": [
            {"role": "system", "content": ai.get("system_prompt", "")},
            {"role": "user", "content": prompt_text},
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
        print(f"{RED}AI request failed: {exc}{RESET}")
        return None


def _whitelist_menu(cfg: Config) -> None:
    while True:
        wl = cfg.get("whitelist", [])
        box(
            "whitelist",
            [
                f"{len(wl)} user(s): {', '.join(wl) or 'empty'}",
                "",
                f"{CYAN}1{RESET}  add user",
                f"{CYAN}2{RESET}  remove user",
                f"{CYAN}3{RESET}  back",
            ],
        )
        choice = prompt("choose", "3").strip()
        if choice == "1":
            name = prompt("username").lstrip("@")
            if name and name not in wl:
                cfg.setdefault("whitelist", []).append(name)
                print(f"  {GREEN}added {name}{RESET}")
        elif choice == "2":
            name = prompt("username").lstrip("@")
            if name in wl:
                wl.remove(name)
                print(f"  {GREEN}removed {name}{RESET}")
        elif choice == "3":
            break


def _handle_thread(client, cfg: Config, thread, seen, last_replied, whitelist_only: bool) -> None:
    msg = _newest_incoming(thread)
    if msg is None:
        return
    sender = _resolve_sender(client, thread, msg)
    if sender is None:
        return
    username = sender.username
    tid = getattr(thread, "id", None) or getattr(thread, "thread_id", None)
    if tid is None:
        return
    key = str(tid)
    if seen.get(key) == msg.id:
        return
    if whitelist_only and username not in cfg.get("whitelist", []):
        return
    now = time.time()
    if last_replied.get(username, 0) + 60 > now:
        return
    prompt_text = f"user @{username} wrote: {msg.text}"
    reply = ai_reply(cfg, prompt_text)
    if not reply:
        reply = f"hey @{username}, I'll get back to you shortly."
    client.direct_send(reply, thread_ids=[_to_int(tid)])
    seen[key] = msg.id
    last_replied[username] = now
    print(f"{DIM}-> @{username}: {reply[:120]}{RESET}")


def chat_loop(client, cfg: Config) -> None:
    """Main AI chat loop: reads recent DMs, replies with AI or canned text.

    Ctrl+C anywhere (poll, per-thread work, sleep) exits cleanly back to
    the menu. A failed send on one thread only skips that thread.
    """
    print("AI chat mode. Press Ctrl+C to exit.")
    ai = cfg.get("ai", {})
    print(f"{DIM}ai.enabled = {ai.get('enabled')}{RESET}")
    whitelist_only = bool(ai.get("whitelist_only"))
    print(f"{DIM}whitelist mode = {WHITELISTED if whitelist_only else EVERYONE}{RESET}")
    seen = {}  # thread id -> last answered message id
    last_replied = {}  # username -> timestamp (secondary guard)
    interval = float(ai.get("poll_interval_seconds", 20))

    while True:
        try:
            threads = _get_recent_messages(client, limit=10)
            for thread in threads:
                try:
                    _handle_thread(client, cfg, thread, seen, last_replied, whitelist_only)
                except KeyboardInterrupt:
                    raise
                except Exception as exc:  # noqa: BLE001 - one bad thread must not stop the loop
                    print(f"{RED}skip thread: {exc}{RESET}")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nbye.")
            return


def run(client, cfg: Config) -> None:
    header("ai chat", "auto-reply to DMs with whitelist control")
    while True:
        box(
            "ai chat",
            [
                f"{CYAN}1{RESET}  chat (reply to DMs automatically)",
                f"{CYAN}2{RESET}  whitelist management",
                f"{CYAN}3{RESET}  back",
            ],
        )
        choice = prompt("choose", "3").strip()
        if choice == "1":
            chat_loop(client, cfg)
        elif choice == "2":
            _whitelist_menu(cfg)
        elif choice == "3":
            return