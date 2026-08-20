"""Leave group chat tool.

Lists your group chats (threads with 2+ other users), lets you pick
one or several, and leaves them. Progress tracked in a done-file.
"""

from colorama import Fore

from actions import (
    AbortedError,
    DIM,
    ERR,
    RESET,
    WARN,
    append_done,
    confirm,
    maybe_batch_pause,
    read_done_file,
    sleep_between_actions,
    Config,
)

DONE = Fore.GREEN


def _list_groups(client):
    threads = []
    try:
        for thread in client.direct_threads(amount=100):
            users = getattr(thread, "users", [])
            if len(users) >= 2:
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
    groups = _list_groups(client)
    if not groups:
        print(f"{DIM}no group chats found.{RESET}")
        return

    print(f"found {len(groups)} group chats:")
    for idx, thread in enumerate(groups, 1):
        print(f"  {idx}) {_group_label(thread)}")

    print("\nleave mode:")
    print("  1) one group (pick by number)")
    print("  2) multiple groups (numbers, comma separated)")
    choice = input(f"{WARN}choose:{RESET} ").strip()
    if choice == "2":
        raw = input(f"{WARN}numbers:{RESET} ").strip()
        try:
            indices = [int(x) for x in raw.replace(",", " ").split()]
        except ValueError:
            print(f"{ERR}invalid numbers.{RESET}")
            return
    else:
        try:
            n = int(input(f"{WARN}group number:{RESET} ").strip())
        except ValueError:
            print(f"{ERR}invalid number.{RESET}")
            return
        indices = [n]

    targets = [groups[i - 1] for i in indices if 1 <= i <= len(groups)]
    if not targets:
        print(f"{ERR}no valid groups selected.{RESET}")
        return
    print(f"will leave {len(targets)} group chat(s)")
    if not confirm("proceed?"):
        print("cancelled.")
        return

    done_file = "leave-chat-done.txt"
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
    print(f"{DIM}finished: {done_count} left, {total - done_count} remaining.{RESET}")