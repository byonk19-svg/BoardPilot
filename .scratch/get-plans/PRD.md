# Get plans

Status: ready-for-agent

The user approved one Get plans action: generate measured drawings, plan stock,
then package a downloadable ZIP from one saved revision. Keep everything local
and offline. Preserve the existing document-corpus follow-up and user sample.

Use the existing persistent jobs and immutable cumulative artifact sets. The UI
chains explicit result-set IDs rather than reading the changing preferred set.
Job idempotency keys identify the run/step/attempt so reload and lost responses
reconnect to the ledger. A failed step requires an explicit retry; successful
steps are retained. No new backend job type, database migration or dependency.

## Acceptance

1. Get plans is the primary packet action. Individual tools remain available.
2. Show drawings, stock and ZIP progress and the saved revision number.
3. Every child job, downloaded PDF/CSV/stock file and ZIP uses that same revision.
   Package the exact cumulative stock result including drawings; never substitute
   a different preferred set. Refuse mismatched or incomplete results.
4. Reload resumes an existing run. Retry reconnects after unknown submission or
   polling outcomes, and retries only failed/cancelled/interrupted work without
   regenerating successful earlier steps. Guard duplicate clicks.
5. Prior downloads remain usable on failure. Incomplete stock is clearly reported
   and cannot be presented as a complete plans package. Navigation stops the old
   controller from updating or queuing work for a different displayed revision.
6. Test change measurements -> Update design -> genuine CAD -> Get plans -> real
   drawings/stock/ZIP, including reload/lost-response recovery. Independently
   inspect ZIP inventories/hashes and revision binding. Exercise protocol failures,
   keyboard and narrow-screen access; run the full relevant verification.

No push, cloud/provider calls, pin changes or unrelated cleanup. Record evidence,
commands and remaining gates in docs/IMPLEMENTATION-STATUS.md and a focused report.
