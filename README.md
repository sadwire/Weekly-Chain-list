# Weekly-Chain-list

Fetch weekly list of updated new EVM Chains from Chainlist and email the diff.

## Overview

This repo runs a scheduled GitHub Actions workflow that:

1. Fetches `https://chainlist.org/rpcs.json`.
2. Normalizes by `chainId` (used as the unique identifier).
3. Compares against the last snapshot in `data/chainlist_snapshot.json`.
4. Sends an email with the list of **new** chain IDs detected since the previous run.
5. Updates the snapshot and commits it back to the repo.

Only new chain IDs are reported; metadata changes to existing chains are ignored.

## Repo layout

- `src/chainlist_diff.py`: fetch + diff logic and report generation.
- `src/emailer.py`: SMTP email helper.
- `data/chainlist_snapshot.json`: stored snapshot for diffing.
- `.github/workflows/weekly_chainlist.yml`: scheduled workflow.
- `tests/`: pytest unit tests.

## Configuration (GitHub)

Set the following **Secrets** in your repository:

- `EMAIL_TO` (recipient)
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `EMAIL_FROM` (optional; defaults to `SMTP_USER`)

Set the following **Variables** in your repository (optional):

- `SEND_IF_ZERO` (`true`/`false`) – when false (default), skip email if there are no new chains.

## Schedule / timezone

The workflow is scheduled in UTC using:

```
0 23 * * 0
```

This corresponds to **Monday 09:00 Australia/Sydney** during standard time (UTC+10). During daylight savings it will run at 10:00 Sydney time. Adjust the cron expression if you want a fixed local time year-round.

## How snapshot updates/commits work

The workflow always writes the latest snapshot to `data/chainlist_snapshot.json`. If that file changes, the workflow commits and pushes the update using `GITHUB_TOKEN` with `contents: write` permissions. This ensures the next run compares against the last successful snapshot.

## How to run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export EMAIL_TO="you@example.com"
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USER="user@example.com"
export SMTP_PASS="yourpassword"
# optional
export EMAIL_FROM="user@example.com"
export SEND_IF_ZERO="true"

python -m src.chainlist_diff
```

## Testing

```bash
pytest
```
