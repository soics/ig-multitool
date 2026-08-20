# Instagram Multi-Tool

CLI automation for Instagram: AI chat with whitelist control, mass
unfollow, remove followers, and leave group chats. Built with
[instagrapi](https://github.com/subzeroid/instagrapi) (private API).

> **Terms of Service notice:** automating Instagram can get your
> account flagged or banned. Use at your own risk, keep the pacing
> delays reasonable, and don't run bulk actions at scale on an account
> you care about.

## Features

- **AI chat** - automatic DM reply loop against any OpenAI-compatible
  `/v1/chat/completions` endpoint (works with local gateways like
  9Router). Optional whitelist: only whitelisted users' DMs get
  replied to.
- **Mass unfollow** - all, non-mutuals only, a selected list, or a
  plain count.
- **Remove followers** - amount, all, or non-mutuals (removes via
  follower removal, not blocking).
- **Leave group chat** - pick one or several group threads.
- **Safe pacing** - randomized delays between actions, batch pauses,
  count confirmation before anything runs, and Ctrl+C-safe progress
  tracking that resumes where it stopped.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config.example.json config.json   # then fill in your details
```

### config.json

| key | meaning |
| --- | --- |
| `username` / `password` | Instagram login (session is cached to `session.json`) |
| `pacing.action_delay_min/max` | random seconds between actions (default 3-15) |
| `pacing.batch_pause_every/seconds` | pause after every N actions (default 60s per 10) |
| `ai.enabled` | on/off for the AI chat tool |
| `ai.base_url` / `ai.api_key` / `ai.model` | OpenAI-compatible endpoint |
| `ai.system_prompt` | persona for the AI replies |
| `whitelist` | usernames allowed in whitelist-only chat mode |

`config.json` is gitignored - never commit it. Only
`config.example.json` is public.

## Usage

```bash
python main.py          # interactive menu
python main.py --chat   # jump straight into AI chat
```

## Roadmap

- Mass follow (targeted lists / unfollow-then-follow cycles)
- Media downloader (posts, reels, stories)
- Post scheduler
- Selenium/Playwright fallback for accounts hit by action blocks

## Disclaimer

This project is for educational purposes. Unauthorized automation
against Instagram may violate Instagram's Terms of Service and can
result in permanent action blocks. You are responsible for how you use
it.