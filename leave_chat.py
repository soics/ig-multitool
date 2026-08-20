"""Leave group chat tool.

Lists your group chats (threads with 2+ other users), lets you pick
one or several, and leaves them. Progress tracked in a done-file.

Cross-platform: paths resolve relative to the project dir, not CWD.
"""

from pathlib import Path

from actions import (
    AbortedError,
    DIM,
    ERR,
    RESET,
    WARN,
    append_done,
    confirm,
    maybe_batch_pause,
    pick_number,
    read_done_file,
    sleep_between_actions,
    Config,
)
from ui import GREEN, header, prompt, status

BASE_DIR = Path(__file__).resolve().parent

DONE = GREEN


def _list_groups(client):
    threads = []
    try:
        for thread in client.direct_threads(amount=100):
            users = getattr(thread, "users", [])
            is_group = getattr(thread, "is_group", None)
            if is_group is None:
                is_group = len(users) >= 2
            if is_group:
                threads.append(thread)
    except Exception as exc:  # noqa: BLE001
        print(f"{ERR}cannot list threads: {exc}{RESET}")
    return threads


def _group_label(thread) -> str:
    users = getattr(thread, "users", [])
    names = [u.username for u in users[:3]]
    extra = f"+{len(users) - 3}" if len(users) > 3 else ""
    return ", ".join(names) + extra


def run(client, cfg: Config) -> None:
    header("leave group chat", "exit one or several group threads")
    groups = _list_groups(client)
    if not groups:
        print(f"{DIM}no group chats found.{RESET}")
        return

    print(f"  found {len(groups)} group chats:")
    for idx, thread in enumerate(groups, 1):
        print(f"    {idx}) {_group_label(thread)}")

    print("\n  leave mode:")
    print("    1) one group (pick by number)")
    print("    2) multiple groups (numbers, comma separated)")
    choice = prompt("choose", "1").strip()
    if choice == "2":
        while True:
            raw = prompt("numbers")
            try:
                indices = [int(x) for x in raw.replace(",", " ").split()]
                break
            except ValueError:
                print(f"{ERR}Enter numbers separated by commas or spaces.{RESET}")
    else:
        n = pick_number("group number", 1, len(groups))
        indices = [n]

    targets = [groups[i - 1] for i in indices if 1 <= i <= len(groups)]
    if not targets:
        print(f"{ERR}no valid groups selected.{RESET}")
        return
    print(f"  will leave {len(targets)} group chat(s)")
    if not confirm("proceed?"):
        print("  cancelled.")
        return

    done_file = str(BASE_DIR / "leave-chat-done.txt")
    done = read_done_file(done_file)
    total = len(targets)
    done_count = 0
    try:
        for thread in targets:
            tid = getattr(thread, "thread_id", None) or thread.id
            if str(tid) in done:
                done_count += 1
                continue
            client.direct_thread_leave(tid)
            append_done(done_file, str(tid))
            done_count += 1
            print(f"  {DONE}left{RESET} {_group_label(thread)}")
            maybe_batch_pause(cfg, done_count)
            sleep_between_actions(cfg)
    except AbortedError:
        print(f"\n{WARN}stopped early - {done_count}/{total} done.{RESET}")
    except KeyboardInterrupt:
        print(f"\n{WARN}interrupted - {done_count}/{total} done (resume-safe).{RESET}")
    except Exception as exc:  # noqa: BLE001
        print(f"{ERR}error: {exc}{RESET}")
    status(done_count == total, f"{done_count}/{total} left, resume file at {done_file}")