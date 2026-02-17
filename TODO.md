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

*Last updated: 2026-02-16*
