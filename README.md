# Jobseeker AI Agent

Initial runnable baseline for a job search assistant.

## For A Novice Reader

This dashboard lets you paste a job description or describe the kind of role you
want, then search recent job listings. It is intentionally strict: it only keeps
jobs that say they are remote, global or worldwide, and suitable for candidates
whose primary language is English.

It also uses fuzzy word matching, so close wording, plural forms, and small
spelling differences can still count as a match.

## For A Technical Reader

The project provides a Streamlit dashboard and a small job-search/filtering
module. It queries public remote job APIs, normalizes listing data, filters by
posting age, remote/global language, English-primary evidence, and non-global
location exclusions, then scores remaining listings against the supplied profile
with dependency-free fuzzy token matching and deduped related terms. The current
strict filters are known to return zero usable matches for some search profiles.

## Dashboard

The dashboard accepts a job description or search profile, searches public
remote-job sources, and keeps only listings that match all strict filters:

- posted within Last 3 days, One week, Two weeks, or One month
- listed as remote and global/worldwide/work-from-anywhere
- includes explicit English-language candidate evidence
- excludes obvious non-English-primary language roles such as French or Spanish speaker postings
- supports fuzzy word matching so close terms, plurals, and small spelling differences can still score against the pasted description

Run the dashboard:

```powershell
python -m streamlit run dashboard.py --server.port 8511 --server.address localhost
```

Open:

```powershell
start chrome http://localhost:8511
```

## Run

```powershell
python jobseeker.py "Data Analyst" --skills python sql excel
```

For machine-readable output:

```powershell
python jobseeker.py "Data Analyst" --skills python sql --format json
```

## Verify

```powershell
python -m pip install -r requirements.txt
python -m unittest -q
```
