# Local desktop launcher

Status: Complete and verified
Baseline: 4cbd5dd05e691db05b2e86f71dff94a2263a1b81

The user approved a simple local launcher, startup and reconnect verification,
offline operation, and no push. Use a Windows desktop shortcut backed by the
installed Python windowed runtime. No terminal, new dependencies, downloads,
login service, or firewall changes are needed.

The shortcut records this checkout and the existing authoritative project data
directory in a per-user config outside the repository. Start only on loopback,
wait for readiness, then open the browser. Repeated clicks reuse the matching
service. A different application, checkout, or data directory on the same port
must produce an understandable error and preserve both stores. Serialize clicks
across launcher processes. Show startup failures in a Windows message box with
the local log location.

Agreed verification seams (from the user's startup/reconnect request):

- Desktop entry point: install and invoke the actual shortcut; no console window.
- Launcher/service boundary: real cold start, readiness, repeated/concurrent
  invocation, incompatible listener, failed startup, and recovery.
- Browser/API boundary: existing tab reconnects after restarting the service;
  saved revision, cut list, and files still belong to that revision. Exercise
  edits only in an isolated local store. Check the actual bookcase read-only.

Use Matt's implement, tdd, and code-review workflow. Existing approval defines
the design; routine launcher details do not require another approval round.
Preserve the unrelated document-corpus changes and audit artifacts present at
the baseline. Commit only this task's changes locally after verification.
