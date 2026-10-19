# Changelog

All notable changes to this package are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-19

### Added

- `CareJobs` client with `search_jobs`, `get_pay`, `get_job_market`, `get_jobs_by_state`,
  `list_employers` and `get_employer`. Each returns a `dict` of the CareJobs.Now MCP tool's
  data that also carries the readable summary as `.text`.
- Low-level `list_tools()` and `call_tool()` for any tool the server adds later.
- `CareJobsError` with a `code` of `tool`, `rpc`, `http`, `network`, `timeout` or `protocol`.
- `Kind`, `Care`, `EmployerType` and `Sort` literal types and the `KINDS`, `CARE_TYPES`,
  `EMPLOYER_TYPES` and `SORTS` tuples, taken from the live `tools/list` schemas.
- `carejobs` command line tool (also `python -m carejobs`): `search`, `pay`, `market`, `state`,
  `employers` and `employer`, with a readable default and `--json` for raw output.
- Standard library only. Python 3.9 or newer. Ships `py.typed`.

[1.0.0]: https://github.com/yumaheymans/carejobs-python/releases/tag/v1.0.0
