"""The ``carejobs`` command line tool."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence

from ._version import __version__
from .client import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, CareJobs, CareJobsError, Result
from .types import CARE_TYPES, EMPLOYER_TYPES, KINDS, SORTS

# Short names people type for a kind. The API itself only knows the exact kinds.
KIND_ALIASES: Dict[str, str] = {
    "registered-nurse": "nurses",
    "registered-nurses": "nurses",
    "nurse": "nurses",
    "rn": "nurses",
    "lpn": "nurses",
    "lvn": "nurses",
    "np": "nurse-practitioners",
    "nps": "nurse-practitioners",
    "pa": "nurse-practitioners",
    "pas": "nurse-practitioners",
    "nurse-practitioner": "nurse-practitioners",
    "physician-assistant": "nurse-practitioners",
    "doctor": "physicians",
    "doctors": "physicians",
    "physician": "physicians",
    "cna": "nursing-assistants",
    "cnas": "nursing-assistants",
    "pct": "nursing-assistants",
    "nursing-assistant": "nursing-assistants",
    "caregiver": "caregivers",
    "home-health-aide": "caregivers",
    "therapy": "therapy-rehab",
    "therapist": "therapy-rehab",
    "mental-health-care": "mental-health",
    "pharmacist": "pharmacy",
    "surgical-tech": "surgical-techs",
    "surgical": "surgical-techs",
    "ems": "emts-paramedics",
    "emt": "emts-paramedics",
    "paramedic": "emts-paramedics",
    "medical-assistant": "medical-assistants",
    "ma": "medical-assistants",
}

EPILOG = (
    "Kinds: " + ", ".join(KINDS) + "\n"
    "Common short names work too (rn, cna, np, doctor, ...).\n"
    "Care types: " + ", ".join(CARE_TYPES) + "\n"
    "No API key needed. MCP server: https://carejobs.now/api/mcp"
)


def parse_kind(value: str) -> str:
    key = "-".join(value.strip().lower().replace("_", " ").split())
    if key in KINDS:
        return key
    if key in KIND_ALIASES:
        return KIND_ALIASES[key]
    raise argparse.ArgumentTypeError(f"unknown kind '{value}'. Use one of: {', '.join(KINDS)}")


def _choice(choices: Sequence[str]) -> Callable[[str], str]:
    def parse(value: str) -> str:
        key = value.strip().lower()
        if key in choices:
            return key
        raise argparse.ArgumentTypeError(f"unknown value '{value}'. Use one of: {', '.join(choices)}")

    return parse


def _positive_int(value: str) -> int:
    if not value.isdigit() or int(value) < 1:
        raise argparse.ArgumentTypeError(f"needs a whole number of 1 or more, not '{value}'")
    return int(value)


def _seconds(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError:
        seconds = 0.0
    if not seconds > 0:
        raise argparse.ArgumentTypeError(f"needs a number of seconds above 0, not '{value}'")
    return seconds


def _common(suppress: bool) -> argparse.ArgumentParser:
    # The same options on the main parser and on every command, so they work in either place.
    # On the commands the default is suppressed, so a value given before the command survives.
    default: Any = argparse.SUPPRESS if suppress else None
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS if suppress else False,
        help="print the raw data as JSON instead of a readable summary",
    )
    parser.add_argument(
        "--base-url",
        default=default if suppress else DEFAULT_BASE_URL,
        metavar="URL",
        help=f"API host (default {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=_seconds,
        default=default if suppress else DEFAULT_TIMEOUT,
        metavar="SEC",
        help=f"give up after this many seconds (default {DEFAULT_TIMEOUT:g})",
    )
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="carejobs",
        description="Search US healthcare jobs and the pay employers post (https://carejobs.now).",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[_common(suppress=False)],
    )
    parser.add_argument("-v", "--version", action="version", version=f"carejobs {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    shared = _common(suppress=True)

    def command(name: str, help: str) -> argparse.ArgumentParser:
        return commands.add_parser(
            name,
            help=help,
            description=help,
            epilog=EPILOG,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            parents=[shared],
        )

    kind_help = "kind of job (nurses, physicians, nursing-assistants, ...)"

    search = command("search", "search open jobs")
    search.add_argument("words", nargs="*", metavar="WORDS", help="words every job must carry, e.g. \"icu nurse\"")
    search.add_argument("--query", help="same as WORDS")
    search.add_argument("--kind", type=parse_kind, help=kind_help)
    search.add_argument("--employer", help="employer slug or name, e.g. kaiser-permanente")
    search.add_argument("--state", help="US state: two-letter code or name")
    search.add_argument("--remote", action="store_true", help="only remote jobs")
    search.add_argument("--min-hourly", type=_positive_int, metavar="USD", help="only jobs whose posted hourly ceiling reaches this")
    search.add_argument("--sort", type=_choice(SORTS), metavar="{" + ",".join(SORTS) + "}", help="default mixed")
    search.add_argument("--limit", type=_positive_int, metavar="N", help="1 to 25 (default 10)")

    pay = command("pay", "posted hourly pay")
    pay.add_argument("--kind", type=parse_kind, help=kind_help)
    pay.add_argument("--employer", help="employer slug or name")

    command("market", "how many jobs are open, by kind, state and employer")

    state = command("state", "open jobs in one state (no state: every state)")
    state.add_argument("state", nargs="?", help="US state: two-letter code or name")
    state.add_argument("--kind", type=parse_kind, help=kind_help + " (needs a state)")
    state.add_argument("--limit", type=_positive_int, metavar="N", help="how many newest jobs, 1 to 25")

    employers = command("employers", "list employers, most open jobs first")
    employers.add_argument("words", nargs="*", metavar="WORDS", help="part of the name")
    employers.add_argument("--query", help="same as WORDS")
    employers.add_argument("--type", type=_choice(EMPLOYER_TYPES), metavar="{" + ",".join(EMPLOYER_TYPES) + "}")
    employers.add_argument("--care", type=_choice(CARE_TYPES), metavar="CARE", help="kind of care, e.g. home-care")
    employers.add_argument("--state", help="employers with open jobs in this state")
    employers.add_argument("--kind", type=parse_kind, help="employers with open jobs of this " + kind_help)
    employers.add_argument("--limit", type=_positive_int, metavar="N", help="1 to 100 (default 20)")

    employer = command("employer", "one employer")
    employer.add_argument("slug", help="employer slug or name, e.g. kaiser-permanente")
    return parser


def _run(client: CareJobs, args: argparse.Namespace) -> Result:
    name = args.command
    if name == "search":
        query = " ".join(args.words) or args.query
        return client.search_jobs(
            query or None,
            kind=args.kind,
            employer=args.employer,
            state=args.state,
            remote=True if args.remote else None,
            min_hourly_usd=args.min_hourly,
            sort=args.sort,
            limit=args.limit,
        )
    if name == "pay":
        return client.get_pay(kind=args.kind, employer=args.employer)
    if name == "market":
        return client.get_job_market()
    if name == "state":
        return client.get_jobs_by_state(args.state, kind=args.kind, limit=args.limit)
    if name == "employers":
        query = " ".join(args.words) or args.query
        return client.list_employers(
            query or None,
            type=args.type,
            care=args.care,
            state=args.state,
            kind=args.kind,
            limit=args.limit,
        )
    return client.get_employer(args.slug)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the CLI. Returns the exit code: 0 ok, 1 the API answered with an error, 2 bad usage."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")  # never die on a character the terminal cannot show
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    client = CareJobs(base_url=args.base_url, timeout=args.timeout, user_agent=f"carejobs-cli/{__version__}")
    try:
        result = _run(client, args)
    except CareJobsError as error:
        print(f"carejobs: {error}", file=sys.stderr)
        return 1
    try:
        if args.json:
            print(json.dumps(dict(result), indent=2, ensure_ascii=False))
        else:
            print(result.text)
        sys.stdout.flush()
    except BrokenPipeError:
        # The reader went away, e.g. `carejobs market | head`. Quit quietly.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
