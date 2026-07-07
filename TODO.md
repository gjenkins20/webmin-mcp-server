# TODO

Project tasks and planned work for webmin-mcp-server.

---

## Publication

- [x] **Plan open source publication**
  - License review (MIT in place)
  - README polished (badges, quick start, tool summary table, links)
  - CONTRIBUTING.md written
  - API reference split to docs/api-reference.md
  - Project URLs added to pyproject.toml

- [x] **Plan Docker Hub publication**
  - Dockerfile created (multi-stage build, non-root user)
  - GitHub Actions workflow for auto-build on push/tag
  - Tagging: semver, branch, SHA
  - Docker Hub image: gjenkins20/webmin-mcp-server

---

## Unfinished API Modules

From `docs/webmin_api_map.md` - endpoints to be documented and implemented:

- [x] `quota::` — Disk quota management
- [x] `passwd::` — Password changes (covered by existing `change_password` via `useradmin::modify_user`)
- [x] `acl::` — Webmin ACL management
- [ ] `firewall::` — Firewall rules (deferred — niche use case, high risk via AI; add if requested)
- [ ] `bind8::` — DNS configuration (deferred — most users use hosted DNS; add if requested)

---

## Maintenance

- [x] **Webmin API audit (through 2.650) — apply auth/RPC updates**
  - [x] Improve 2FA/RPC auth error message in `src/webmin_client.py` (~211–225) — verified end-to-end against a real, patched, 2FA-enrolled account
  - [x] Document RPC/API-only accounts (Webmin 2.650) in README setup
  - [x] Verify 2.630 input-validation tightening via `tests/live_test_phase7.py` — ran against a live upgraded server, all calls behaved correctly
  - [x] Document RPC timeout config option (2.620)
  - Full audit: `docs/webmin-api-audit-2026-06.md`

---

## Completed

- [x] `software::` — Package management (read-only)
- [x] `smart-status::` — SMART disk health
- [x] `lvm::` — Logical Volume Manager
- [x] `backup-config::` — Configuration backups
- [x] `webminlog::` — Audit log access
- [x] `time::` — System time
- [x] `sshd::` — SSH configuration
- [x] `init::` — Runlevels
- [x] `fail2ban::` — Intrusion prevention
- [x] `mysql::` — Database management

---

*Last updated: 2026-07-07*
