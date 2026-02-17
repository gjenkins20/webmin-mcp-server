# TODO

Project tasks and planned work for webmin-mcp-server.

---

## Publication

- [ ] **Plan open source publication**
  - License review
  - README polish
  - CONTRIBUTING.md

- [ ] **Plan Docker Hub publication**
  - Dockerfile review
  - Build automation
  - Tagging strategy

---

## Unfinished API Modules

From `docs/webmin_api_map.md` - endpoints to be documented and implemented:

- [ ] `quota::` — Disk quota management
- [ ] `passwd::` — Password changes
- [ ] `acl::` — Webmin ACL management
- [ ] `firewall::` — Firewall rules (not available on some systems)
- [ ] `bind8::` — DNS configuration (not available on some systems)

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
