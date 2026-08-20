"""Remove followers tool.

Removes followers from your account (instagrapi's follower removal -
unfollow-by-request style, not blocking). Amount / all / non-mutuals.
Progress tracked in a done-file for safe resume.
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
    human_count,
    maybe_batch_pause,
    pick_number,
    read_done_file,
    sleep_between_actions,
    Config,
)

MODE_AMOUNT = "amount"
MODE_ALL = "all"
MODE_NON_MUTUAL = "non-mutuals"

DONE = Fore.GREEN


def _choose_mode():
    print("\nremove followers mode:")
    print(f"  1) {MODE_AMOUNT}       - remove N followers")
    print(f"  2) {MODE_ALL}         - remove everyone following you")
    print(f"  3) {MODE_NON_MUTUAL}  - remove people you don't follow back")
    choice = input(f"{WARN}choose:{RESET} ").strip()
    return {"1": MODE_AMOUNT, "2": MODE_ALL, "3": MODE_NON_MUTUAL}.get(choice, MODE_AMOUNT)


def run(client, cfg: Config) -> None:
    mode = _choose_mode()
    amount = 0
    if mode == MODE_AMOUNT:
        amount = pick_number("how many to remove", 1)

    followers = client.user_followers(client.user_id)
    followers = list(followers.values())
    if mode == MODE_NON_MUTUAL:
        following = client.user_following(client.user_id)
        following_ids = set(following.keys())
        targets = [u for u in followers if u.pk not in following_ids]
    elif mode == MODE_AMOUNT:
        targets = followers[:amount]
    else:
        targets = followers

    if not targets:
        print(f"{DIM}no followers to remove.{RESET}")
        return

    print(f"will remove {human_count(len(targets))}")
    if not confirm("proceed?"):
        print("cancelled.")
        return

    done_file = "remove-followers-done.txt"
    done = read_done_file(done_file)
    total = len(targets)
    done_count = 0
    try:
        for user in targets:
            handle = user.username
            if handle in done:
                done_count += 1
                continue
            client.remove_follower(user.pk)
            append_done(done_file, handle)
            done_count += 1
            print(f"  {DONE}removed{RESET} {handle}")
            maybe_batch_pause(cfg, done_count)
            sleep_between_actions(cfg)
    except AbortedError:
        print(f"\n{WARN}stopped early - {done_count}/{total} done.{RESET}")
    except KeyboardInterrupt:
        print(f"\n{WARN}interrupted - {done_count}/{total} done (resume-safe).{RESET}")
    except Exception as exc:  # noqa: BLE001
        print(f"{ERR}error: {exc}{RESET}")
    print(f"{DIM}finished: {done_count} removed, {total - done_count} remaining.{RESET}")