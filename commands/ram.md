# /ram

Show current Claude RAM usage. Safe and inline — does NOT quit anything.

## Action
Run exactly this one Bash command and report its one-line output to the user verbatim:

```
powershell -Command "ram"
```

If you want more detail, also note how it compares to the ~1,860 MB baseline measured during setup (on the retired 5.7 GB box; current machine is 32 GB with a ~24 GB working ceiling — retuned 2026-07-09), and remind the user that `/handoff` or `/heavy` frees ~1.3 GB by moving to a lean CLI session.
