# IG Multi Tool

CLI automation for Instagram: **AI chat** with whitelist control,
**mass unfollow**, **remove followers**, and **leave group chats**.
Built with [instagrapi](https://github.com/subzeroid/instagrapi).

Works on **Linux, macOS, and Windows** (Python 3.10+).

> **Terms of Service notice:** automating Instagram can get your
> account flagged or banned. Use at your own risk, keep the pacing
> delays reasonable, and don't run bulk actions at scale on an account
> you care about.

## Features

| tool | what it does |
| --- | --- |
| **AI chat** | automatic DM reply loop against any OpenAI-compatible `/v1/chat/completions` endpoint (local gateways like 9Router work great). Optional whitelist: only whitelisted users' DMs get replied to. |
| **Mass unfollow** | unfollow everyone, skip mutuals, a selected list, or a plain count. |
| **Remove followers** | remove by amount, all, or non-mutuals (follower removal, not blocking). |
| **Leave group chat** | pick one or several group threads and leave them. |

All bulk tools share **safe pacing** (randomized delays, batch pauses,
count confirmation before anything runs) and **resume-safe progress**:
interrupt with `Ctrl+C` any time, rerun, and it continues where it
stopped (tracked in `*-done.txt` files).

## Setup

### 1. Get the code

```bash
git clone https://github.com/soics/ig-multitool.git
cd ig-multitool
```

### 2. Create a virtual environment

<details>
<summary>Linux / macOS</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
```

</details>

<details>
<summary>Windows (PowerShell)</summary>

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

</details>

<details>
<summary>Windows (cmd)</summary>

```cmd
py -m venv .venv
.venv\Scripts\activate.bat
```

</details>

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure

```bash
cp config.example.json config.json
```

Edit `config.json` and fill in your Instagram credentials.

### config.json

| key | meaning |
| --- | --- |
| `username` / `password` | Instagram login (session is cached to `session.json`) |
| `pacing.action_delay_min/max` | random seconds between actions (default 3-15) |
| `pacing.batch_pause_every/seconds` | pause after every N actions (default 60s per 10) |
| `ai.enabled` | on/off for the AI chat tool |
| `ai.base_url` / `ai.api_key` / `ai.model` | OpenAI-compatible endpoint (e.g. `http://localhost:20128/v1`, `ollama/gpt-oss:120b`) |
| `ai.system_prompt` | persona for the AI replies |
| `whitelist` | usernames allowed in whitelist-only chat mode |

`config.json` and `session.json` are gitignored - never commit them.
Only `config.example.json` is public.

## Usage

```bash
python main.py           # interactive menu
python main.py --chat    # jump straight into AI chat
python main.py --preview # browse the whole UI with fake data, no login
```

`--preview` runs every tool against a built-in fake client (sample
accounts, threads, groups) with fast pacing - perfect for seeing the
layout and flow without touching a real account or needing credentials.

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