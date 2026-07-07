# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.1] - 2026-07-07

### Changed
- Clarified the 401/403 authentication error message in the Webmin client
  to mention two-factor authentication and Webmin 2.650+'s RPC/API-only
  account type as likely causes/solutions, instead of a generic
  auth-failed message.
- README setup instructions now recommend provisioning a dedicated
  RPC/API-only Webmin account (2.650+) for the service account, note the
  2FA-on-RPC caveat, and document the RPC timeout config option (2.620+).

### Verified
- Confirmed against a live, current Webmin server that the updated error
  message fires correctly when an account with 2FA enabled attempts an
  RPC call, and that no existing XML-RPC calls are rejected by Webmin
  2.630's stricter input validation.

## [0.1.0] - 2026-02-16

Initial public release.
