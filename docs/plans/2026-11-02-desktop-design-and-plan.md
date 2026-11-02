# Desktop simulator design and implementation plan

Goal: self-contained Windows x64 desktop client retaining existing simulator page and transactional GPS/IP/target logic; user-editable local MySQL connection; portable ZIP and installer; standalone GitHub project, other-OS build workflows. User confirmed Windows first. Electron choice is implementer's call under explicit delivery request.

Architecture: Electron renders local packaged page, no Node in renderer. Bundled PyInstaller sidecar owns drivers, parameterized SQL, schema validation, transaction lock, bounded auto worker. Electron starts a random loopback port, injects saved profiles over private stdin, stores optional passwords with OS safeStorage, and gracefully stops child on app exit. Connection test is read-only; initialize is explicit and only for signal_sim_*; no destructive reset. API command nonce and strict same-origin/Host guards remain. Secrets never returned via settings or logs. Original webpage service18117 and platform18097 are independent.

Approaches: page-only ZIP leaves Python/browser prerequisites; Python+WebView depends on platform-specific web runtime; Electron+bundled sidecar includes display and engine, costs package size but meets offline-open requirement. Choose third. No new source schema/business changes; original source generation retained, values all synthetic.

Tasks (inline execution; fresh review at end):
- [x] P1 Extract only owned generator/dashboard/schema/tests; create clean independent repo, architecture/reproducible manifests, no platform fixtures/credentials.
- [x] P2 RED/GREEN connection validation, read-only test, atomic profile changes, explicit non-destructive initialization, no secret responses; preserve all original transaction tests.
- [x] P3 RED/GREEN desktop secret-store migration, sender isolation, process readiness/timeout/graceful close; integrate existing page with small connection dialog.
- [x] P4 Native MySQL/PG isolated fixtures, packaged Windows directory no-host-Python/Node startup and real GUI DML/start/stop, move-to-fresh-directory/installer smoke; release zip/sha. See docs/ACCEPTANCE.md and evidence.
- [x] P5 CI Windows/Linux/macOS builds, public README/tutorial/changelog/source attribution, secret scan; fresh remote comparison then explicit authorized upload HEAD->main + v0.1.0release and verify remote SHA/assets. Never push Palantir platform repository.

Delivery: release v0.1.0 points to a1f74db260516a1cbb696b1c151350bc8ef473bd. Windows ZIP/installer published with server-side SHA256 matching local artifacts. First CI run41402659925 passed all five jobs (three OS builds + native MySQL/PostgreSQL). Later documentation closure on main does not change the tested application code. Non-Windows real desktop installation remains unverified.

Review focus: password never echoed or persisted plaintext; renderer cannot invoke arbitrary paths/SQL/process; failed save preserves old profile; profile switch while writer active rejected; initialize rejects partial/foreign tables; close stops engine; ports selected dynamically; packaging includes native drivers and assets and licenses.

Boundaries: local Windows proven separately from configured Linux/macOS CI; app needs a running target database, not a bundled DB server. PostgreSQL generator support does not mean platform WAL ingestion.
