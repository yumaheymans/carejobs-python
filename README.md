# carejobs

Client and command line tool for the [CareJobs.Now](https://carejobs.now) healthcare jobs API. Search open US healthcare jobs, see the pay employers post, and look up employers and states, from Python.

- Free, no API key.
- Standard library only (`urllib`). Python 3.9 or newer.
- Typed (ships `py.typed`), with the job kinds as `Literal` types.
- The same API is a remote MCP server at <https://carejobs.now/api/mcp>, so any MCP client can use it too.

## Install

```sh
pip install carejobs
```

## Quick start

```python
from carejobs import CareJobs

cj = CareJobs()

jobs = cj.search_jobs("icu", state="TX", kind="nurses", limit=5)
print(jobs["total"], "jobs match")
for job in jobs["jobs"]:
    print(job["title"], "|", job["employer"], "|", job["location"], "|", job["url"])

pay = cj.get_pay(kind="nurses")
print("Median posted pay for nurses:", pay["pay"]["median"], "$/hr")

# Every answer also carries the server's readable summary:
print(pay.text)
```

Each method returns a `Result`: a plain `dict` of the tool's data (so `json.dumps(result)` works) with `.text`, a readable plain-text summary written by the server. Keys are the ones the API sends (`typical_low`, `open_jobs`, and so on).

## Client

```python
cj = CareJobs(
    base_url="https://carejobs.now",  # default
    timeout=30.0,                     # seconds, default 30
    user_agent="my-app/1.0",          # default "carejobs-python/<version>"
)
```

### `search_jobs(query=None, *, kind, employer, state, remote, min_hourly_usd, sort, limit)`

Open healthcare jobs at US hospitals, health systems, clinics and care companies, plus the job boards the site reads. Every argument is optional.

| Argument | Meaning |
| --- | --- |
| `query` | Words every job must carry in its title, place, department or schedule ("ICU", "night") |
| `kind` | Kind of job, see below |
| `employer` | Employer slug or name ("kaiser-permanente") |
| `state` | Two-letter code or name ("TX", "Texas") |
| `remote` | `True` for only remote jobs |
| `min_hourly_usd` | Only jobs whose posted hourly ceiling reaches this (1 to 1000) |
| `sort` | `"mixed"` (default), `"newest"` or `"highest_pay"` |
| `limit` | 1 to 25, default 10 |

Returns `total`, `pay`, `jobs` and `more`. `total` counts every match, `jobs` holds the ones returned. Each job has `title`, `employer`, `via`, `kind`, `pay`, `schedule`, `facility`, `location`, `listed`, `url` (its page on CareJobs.Now, where the user applies) and `employer_page`.

### `get_pay(kind=None, employer=None)`

What jobs post as hourly pay, measured from open jobs (before shift differentials and bonuses). The answer depends on the arguments:

```python
cj.get_pay()                                           # every kind of job
cj.get_pay(kind="nurses")                              # one kind, plus the employers posting the most
cj.get_pay(employer="kaiser-permanente")               # one employer, overall and by kind
cj.get_pay(kind="nurses", employer="kaiser-permanente")
```

"Typical" pay runs from the 25th percentile of what jobs pay to the 90th-percentile advertised ceiling. A market rate is reported only where at least three employers post a rate (`market_rate`).

### `get_job_market()`

How many healthcare jobs are open, how many were first listed in the last 7 days, and the open jobs by kind, by state and by employer.

### `get_jobs_by_state(state=None, kind=None, limit=None)`

```python
cj.get_jobs_by_state()                                   # every state
cj.get_jobs_by_state("TX", limit=5)                      # one state: kinds, pay, towns, employers, newest jobs
cj.get_jobs_by_state("OH", kind="nursing-assistants")
```

`kind` needs a `state`. `limit` (1 to 25) is how many of the newest jobs to return.

### `list_employers(query=None, *, type, care, state, kind, limit)`

Employers, AI-training programs and job boards the site reads, most open jobs first. `type` is `"employer"`, `"ai-program"` or `"job-board"`, `care` is one of `CARE_TYPES`, `limit` is 1 to 100 (default 20).

### `get_employer(slug)`

One employer by slug or name: what it is, where it hires, open jobs by kind, posted pay, newest and best-paid jobs, and links to its page, every open job and its own careers site.

### Kinds

`Kind` is a `Literal` type, and `KINDS` is the same list as a tuple:

```
nurses, nurse-practitioners, physicians, nursing-assistants, caregivers,
therapy-rehab, mental-health, pharmacy, imaging, lab, surgical-techs,
emts-paramedics, medical-assistants, dental, admin, allied-health, ai-training
```

`Care`, `EmployerType` and `Sort` (with `CARE_TYPES`, `EMPLOYER_TYPES`, `SORTS`) work the same way. They are copied from the live `tools/list` schemas, and a test checks them against the live server.

### Errors

Every failure is a `CareJobsError` with a `code`:

| `code` | Meaning |
| --- | --- |
| `tool` | The server ran the tool and answered with an error (unknown kind, unknown employer). `str(error)` is the server's explanation. |
| `rpc` | JSON-RPC error (`rpc_code` is set) |
| `http` | Non-2xx HTTP status (`status` is set) |
| `network` | The request never completed |
| `timeout` | No answer within `timeout` seconds |
| `protocol` | The answer was not the MCP shape |

```python
from carejobs import CareJobs, CareJobsError

try:
    CareJobs().get_employer("no-such-employer")
except CareJobsError as error:
    if error.code == "tool":
        print(error)
    else:
        raise
```

The client does not retry. Wrap calls yourself if you need that.

### Low level

`cj.list_tools()` returns the server's tools with their input schemas, and `cj.call_tool(name, arguments)` calls any tool by name (arguments in the API's names), for tools added after this version.

## Command line

```sh
carejobs search "icu nurse" --state TX --limit 5
carejobs pay --kind nurses
carejobs market
carejobs state TX
carejobs employers --query kaiser
carejobs employer kaiser-permanente
```

`python -m carejobs ...` works the same.

| Command | Options |
| --- | --- |
| `search [WORDS]` | `--kind` `--employer` `--state` `--remote` `--min-hourly USD` `--sort` `--limit` |
| `pay` | `--kind` `--employer` |
| `market` | |
| `state [STATE]` | `--kind` `--limit` |
| `employers [WORDS]` | `--query` `--type` `--care` `--state` `--kind` `--limit` |
| `employer SLUG` | |

Options for every command: `--json` prints the raw data as JSON instead of the readable summary, `--base-url`, `--timeout SECONDS`, `--help`, `--version`.

`--kind` takes the exact kinds above and common short names (`rn`, `cna`, `np`, `doctor`, `registered-nurse` and a few more). The exit code is 0 on success, 1 when the API answers with an error, and 2 for bad usage.

## About the data

Jobs are read daily from the career sites of US hospitals, health systems and care employers. Pay is the hourly rate the employer posts, not a survey of what everyone in a field earns, and only jobs that post a rate count toward it. The board covers the employers it reads, not the whole labor market. Method: <https://carejobs.now/methodology>.

The CareJobs.Now data files (`/roles.json` and `/pay.json`) are published under CC BY 4.0, so credit CareJobs.Now when you use the numbers. See <https://carejobs.now/data> for the files, the OpenAPI description and the current terms.

## Links

- Site: <https://carejobs.now>
- Data and API docs: <https://carejobs.now/data>
- MCP server: <https://carejobs.now/api/mcp>
- OpenAPI spec: <https://github.com/yumaheymans/carejobs-mcp>
- npm package: `npm install carejobs`

## License

MIT, Copyright 2026 CareJobs.Now. The license covers this package's code, not the data it fetches.
