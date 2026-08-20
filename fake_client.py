"""Fake instagrapi client for `python main.py --preview`.

Mimics just enough of the instagrapi API surface that all tools can run
against it with sample data - no login, no network, no rate limits.
Lets you see the whole UI flow without touching a real account.

Every mutation prints `[fake] ...` and the client carries an `is_fake`
flag, so preview data can never be mistaken for real account activity.
"""

from datetime import datetime, timedelta

START = datetime(2026, 8, 1, 12, 0, 0)


class FakeUser:
    def __init__(self, pk: int, username: str, full_name: str = ""):
        self.pk = pk
        self.username = username
        self.full_name = full_name

    def __repr__(self):
        return f"FakeUser({self.username})"

    def __str__(self):
        return self.username


class FakeMessage:
    def __init__(
        self,
        msg_id: str,
        text: str,
        user_id: str,
        timestamp: datetime,
        is_sent_by_viewer: bool = False,
    ):
        self.id = msg_id
        self.text = text
        self.user_id = user_id
        self.timestamp = timestamp
        self.is_sent_by_viewer = is_sent_by_viewer

    def __repr__(self):
        return f"FakeMessage({self.id}, {self.text!r})"


class FakeThread:
    def __init__(
        self,
        thread_id: str,
        users,
        messages=None,
        pending: bool = False,
        is_group: bool = True,
    ):
        self.thread_id = thread_id
        self.id = thread_id
        self.users = users
        self.messages = list(messages or [])
        self.pending = pending
        self.is_group = is_group

    def __repr__(self):
        return f"FakeThread({self.thread_id}, users={len(self.users)})"

    def __str__(self):
        names = ", ".join(u.username for u in self.users[:2])
        return f"@{names}: \"hey, what's up?\"" if not self.messages else f"@{names}: {self.messages[-1].text}"


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
    is_fake = True

    def __init__(self):
        self.user_id = 1
        self._following = {}
        self._followers = {}
        self._threads = []
        self._msg_counter = 0
        self._seed()

    def _new_message(self, text, user_id, offset_minutes, is_sent_by_viewer=False):
        self._msg_counter += 1
        return FakeMessage(
            f"m{self._msg_counter}",
            text,
            str(user_id),
            START + timedelta(minutes=offset_minutes),
            is_sent_by_viewer=is_sent_by_viewer,
        )

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
            FakeThread(
                "1001",
                [self._following[2], self._following[3], self._following[4]],
                messages=[
                    self._new_message("welcome back, everyone!", self.user_id, 0, is_sent_by_viewer=True),
                    self._new_message("hey, what's up?", 2, 1),
                ],
                is_group=True,
            ),
            FakeThread(
                "1002",
                [self._following[5], self._following[6]],
                messages=[
                    self._new_message("nice banner!", 6, 2),
                ],
                is_group=False,
            ),
            FakeThread(
                "1003",
                [self._following[7], self._following[8], self._following[9], self._following[10]],
                messages=[
                    self._new_message("hello?", 7, 3),
                ],
                pending=True,
                is_group=True,
            ),
            FakeThread(
                "1004",
                [self._following[11], self._following[12], self._following[13]],
                messages=[],
                is_group=True,
            ),
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

    def direct_thread(self, thread_id, amount=20):
        tid = str(thread_id)
        for thread in self._threads:
            if str(thread.id) == tid:
                return thread
        raise ValueError(f"no fake thread {tid}")

    def direct_messages(self, thread_id, amount=0):
        thread = self.direct_thread(thread_id)
        if amount and amount > 0:
            return thread.messages[:amount]
        return list(thread.messages)

    def direct_send(self, text, user_ids=(), thread_ids=(), **kwargs):
        print(f"  [fake] direct_send({text!r}, thread_ids={list(thread_ids)})")
        sent = []
        for tid in thread_ids:
            thread = self.direct_thread(tid)
            thread.messages.append(
                self._new_message(text, self.user_id, 60, is_sent_by_viewer=True)
            )
            sent.append(thread.id)
        return sent

    def direct_thread_leave(self, thread_id):
        print(f"  [fake] direct_thread_leave({thread_id})")