"""Mass unfollow tool.

Unfollows accounts you follow, optionally skipping mutuals, optionally
restricted to a selected group (list of usernames) or a plain count.
Progress is tracked in a done-file so an interrupted run can be resumed
without re-touching already-processed accounts.

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
    human_count,
    maybe_batch_pause,
    pick_number,
    read_done_file,
    sleep_between_actions,
    Config,
)
from ui import GREEN, header, prompt, status

BASE_DIR = Path(__file__).resolve().parent

MODE_ALL = "all"
MODE_NON_MUTUAL = "non-mutuals"
MODE_SELECTED = "selected"
MODE_COUNT = "count"

DONE = GREEN


def _choose_mode():
    print("\n  unfollow mode:")
    print(f"    1) {MODE_ALL}          - everyone you follow")
    print(f"    2) {MODE_NON_MUTUAL}  - skip people who follow you back")
    print(f"    3) {MODE_SELECTED}     - a specific list (comma separated usernames)")
    print(f"    4) {MODE_COUNT}        - just N accounts")
    choice = prompt("choose", "1").strip()
    return {"1": MODE_ALL, "2": MODE_NON_MUTUAL, "3": MODE_SELECTED, "4": MODE_COUNT}.get(choice, MODE_ALL)


def _selected_list():
    raw = prompt("usernames (comma separated)")
    return [u.strip().lstrip("@") for u in raw.split(",") if u.strip()]


def run(client, cfg: Config) -> None:
    header("mass unfollow", "clean up your following list")
    mode = _choose_mode()
    selected = _selected_list() if mode == MODE_SELECTED else None
    count = 0
    if mode == MODE_COUNT:
        count = pick_number("how many to unfollow", 1)
    if mode == MODE_SELECTED and not selected:
        print(f"{ERR}no usernames given.{RESET}")
        return

    following = client.user_following(client.user_id)
    following = list(following.values())
    if mode == MODE_NON_MUTUAL:
        followers = client.user_followers(client.user_id)
        follower_ids = {str(k) for k in followers.keys()}
        targets = [u for u in following if str(u.pk) not in follower_ids]
    elif mode == MODE_SELECTED:
        wanted = set(selected or [])
        targets = [u for u in following if u.username in wanted]
        missing = wanted - {u.username for u in targets}
        if missing:
            print(f"{WARN}not found in following: {', '.join(sorted(missing))}{RESET}")
    elif mode == MODE_COUNT:
        targets = following[:count]
    else:
        targets = following

    if not targets:
        print(f"{DIM}nothing to unfollow.{RESET}")
        return

    print(f"  will unfollow {human_count(len(targets))}")
    if not confirm("proceed?"):
        print("  cancelled.")
        return

    done_file = str(BASE_DIR / "unfollow-done.txt")
    done = read_done_file(done_file)
    progress_total = len(targets)
    done_count = 0
    try:
        for user in targets:
            handle = user.username
            if handle in done:
                done_count += 1
                continue
            client.user_unfollow(user.pk)
            append_done(done_file, handle)
            done_count += 1
            print(f"  {DONE}unfollowed{RESET} {handle}")
            maybe_batch_pause(cfg, done_count)
            sleep_between_actions(cfg)
    except AbortedError:
        print(f"\n{WARN}stopped early - {done_count}/{progress_total} done.{RESET}")
    except KeyboardInterrupt:
        print(f"\n{WARN}interrupted - {done_count}/{progress_total} done (resume-safe).{RESET}")
    except Exception as exc:  # noqa: BLE001
        print(f"{ERR}error: {exc}{RESET}")
    status(done_count == progress_total, f"{done_count}/{progress_total} unfollowed, resume file at {done_file}")