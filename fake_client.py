"""Fake instagrapi client for `python main.py --preview`.

Mimics just enough of the instagrapi API surface that all tools can run
against it with sample data - no login, no network, no rate limits.
Lets you see the whole UI flow without touching a real account.
"""

from datetime import datetime


class FakeUser:
    def __init__(self, pk: int, username: str, full_name: str = ""):
        self.pk = pk
        self.username = username
        self.full_name = full_name

    def __repr__(self):
        return f"FakeUser({self.username})"

    def __str__(self):
        return self.username


class FakeThread:
    def __init__(self, thread_id: str, users, pending: bool = False):
        self.thread_id = thread_id
        self.id = thread_id
        self.users = users
        self.pending = pending

    def __repr__(self):
        return f"FakeThread({self.thread_id}, users={len(self.users)})"

    def __str__(self):
        names = ", ".join(u.username for u in self.users[:2])
        return f"@{names}: \"hey, what's up?\""


_NAMES = [
    ("alexnova", "Alex Nova"),
    ("brianna_k", "Brianna K"),
    ("carl_maes", "Carl Maes"),
    ("dana_lou", "Dana Lou"),
    ("erik_w", "Erik W"),
    ("fifi_draws", "Fifi Draws"),
    ("gino_t", "Gino T"),
    ("hannah_rose", "Hannah Rose"),
    ("ivy_lee", "Ivy Lee"),
    ("julio_c", "Julio C"),
    ("kai_banana", "Kai Banana"),
    ("lena_s", "Lena S"),
    ("marcus_x", "Marcus X"),
    ("nina_blue", "Nina Blue"),
    ("otto_b", "Otto B"),
]


class FakeClient:
    def __init__(self):
        self.user_id = 1
        self._following = {}
        self._followers = {}
        self._threads = []
        self._seed()

    def _seed(self):
        for i, (uname, fname) in enumerate(_NAMES, start=2):
            user = FakeUser(i, uname, fname)
            self._following[user.pk] = user
            if i % 3 != 0:
                self._followers[user.pk] = user
        self._followers[FakeUser(99, "not_following_you", "Lurker").pk] = FakeUser(
            99, "not_following_you", "Lurker"
        )
        self._threads = [
            FakeThread("t1", [self._following[2], self._following[3], self._following[4]]),
            FakeThread("t2", [self._following[5], self._following[6]]),
            FakeThread("t3", [self._following[7], self._following[8], self._following[9], self._following[10]], pending=True),
            FakeThread("t4", [self._following[11], self._following[12], self._following[13]]),
        ]

    def user_following(self, user_id):
        return self._following

    def user_followers(self, user_id):
        return self._followers

    def user_unfollow(self, pk):
        print(f"  [fake] user_unfollow({pk})")

    def remove_follower(self, pk):
        print(f"  [fake] remove_follower({pk})")

    def direct_threads(self, amount=0):
        if amount and amount > 0:
            return self._threads[:amount]
        return self._threads

    def direct_thread_leave(self, thread_id):
        print(f"  [fake] direct_thread_leave({thread_id})")