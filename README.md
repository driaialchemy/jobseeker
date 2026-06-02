# Jobseeker AI Agent

Initial runnable baseline for a job search assistant.

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
python -m unittest -q
```
