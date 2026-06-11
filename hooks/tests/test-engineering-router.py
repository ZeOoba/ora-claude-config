# test-engineering-router.py — run: python test-engineering-router.py
import subprocess, json, sys, os
HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engineering-router.py")  # hooks/ (test in hooks/tests/)

def run(prompt):
    p = subprocess.run([sys.executable, HOOK], input=json.dumps({"prompt": prompt}),
                       capture_output=True, text=True)
    assert p.returncode == 0, f"hook must always exit 0, got {p.returncode}: {p.stderr}"
    return p.stdout

cases = [
    ("there's a bug, the rent roll parser is failing", "/debug"),
    ("build a new dashboard widget for WALT", "/build"),
    ("refactor the overlay module, it's too big", "/refactor"),
    ("research which charting library is fastest", "/research"),
    ("ship the brain mirror to production", "/ship"),
]
for prompt, expected in cases:
    out = run(prompt)
    assert expected in out, f"prompt {prompt!r} should suggest {expected}, got: {out!r}"
    assert out.isascii(), f"hook output must be ASCII-only (Windows cp1252 console safe); non-ASCII in: {out!r}"

# Still-firing core cases (explicit / unambiguous action prompts)
firing = [
    ("the rent roll parser throws an error", "/debug"),
    ("build a new dashboard widget", "/build"),
    ("ship the brain mirror to production", "/ship"),
]
for prompt, expected in firing:
    out = run(prompt)
    assert expected in out, f"prompt {prompt!r} should suggest {expected}, got: {out!r}"
    assert out.isascii(), f"hook output must be ASCII-only (Windows cp1252 console safe); non-ASCII in: {out!r}"

# Silence on non-work prompts and empty prompts (no false nudges)
assert run("what's the weather") == "", "should stay silent on non-coding prompts"
assert run("") == "", "should stay silent on empty prompt"

# Negative-context regression cases: analytical/meta/scheduling -> MUST stay silent
silent = [
    "Assume this engineering operating system isn't perfect and fails more often than it should. Explain why this would happen and suggest improvements.",
    "explain why the deploy keeps failing in general terms",
    "remind me to debug this tomorrow",
    "what are the tradeoffs of refactoring vs rewriting",
]
for prompt in silent:
    out = run(prompt)
    assert out == "", f"analytical/meta prompt should stay silent, got: {out!r}"

# Cloud-review confidentiality warning (fix #1b): naming a confidential repo + ultra/cloud review MUST warn -> LOCAL
cr = run("can you run /code-review ultra on oxford-command-center")
assert ("confidential" in cr.lower()) and ("local" in cr.lower()), f"cloud review on confidential repo must warn to use LOCAL, got: {cr!r}"
assert cr.isascii(), f"warning must be ASCII, got: {cr!r}"
# cloud review WITHOUT naming a confidential repo -> no confidentiality flag
cr2 = run("run /code-review ultra on my-public-sandbox")
assert "confidential" not in cr2.lower(), f"should not flag a non-confidential repo, got: {cr2!r}"

print("ALL ROUTER TESTS PASS")
