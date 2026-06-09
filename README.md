# Jobseeker AI Agent

Initial runnable baseline for a job search assistant.

## Dashboard

The dashboard accepts a job description or search profile, searches public
remote-job sources, and keeps only listings that match all strict filters:

- posted within Last 3 days, One week, Two weeks, or One month
- listed as remote and global/worldwide/work-from-anywhere
- includes explicit English-language candidate evidence
- excludes obvious non-English-primary language roles such as French or Spanish speaker postings

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
