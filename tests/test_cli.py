import contextlib
import io
import json
import subprocess
import sys
import unittest

from carejobs import __version__
from carejobs.cli import main


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(list(argv))
        except SystemExit as exit_:
            code = exit_.code if isinstance(exit_.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def test_help_and_version(self):
        code, out, _ = run("--help")
        self.assertEqual(code, 0)
        self.assertIn("search", out)
        code, out, _ = run("--version")
        self.assertEqual((code, out.strip()), (0, f"carejobs {__version__}"))

    def test_no_command_exits_2(self):
        self.assertEqual(run()[0], 2)

    def test_usage_errors_exit_2_without_calling_the_api(self):
        for argv in (
            ["bogus"],
            ["search", "--kind", "plumbers"],
            ["search", "--sort", "random"],
            ["search", "--limit", "x"],
            ["pay", "--remote"],
            ["employer"],
            ["search", "--nope"],
        ):
            code, _, err = run(*argv)
            self.assertEqual(code, 2, argv)
            self.assertIn("error", err)

    def test_pay_with_a_short_kind_name(self):
        code, out, err = run("pay", "--kind", "registered-nurse", "--json")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["kind"], "nurses")

    def test_search_readable_and_json(self):
        code, out, err = run("search", "icu nurse", "--state", "TX", "--limit", "2")
        self.assertEqual(code, 0, err)
        self.assertIn("open healthcare jobs match", out)
        code, out, err = run("search", "icu nurse", "--state", "TX", "--limit", "2", "--json")
        data = json.loads(out)
        self.assertLessEqual(len(data["jobs"]), 2)
        self.assertNotIn("text", data)
        # --json also works before the command
        code, out, err = run("--json", "market")
        self.assertGreater(json.loads(out)["open_jobs"], 1000)

    def test_api_error_exits_1(self):
        code, _, err = run("employer", "no-such-employer-xyz")
        self.assertEqual(code, 1)
        self.assertIn("Unknown employer", err)

    def test_python_dash_m(self):
        done = subprocess.run(
            [sys.executable, "-m", "carejobs", "--version"], capture_output=True, text=True, check=True
        )
        self.assertEqual(done.stdout.strip(), f"carejobs {__version__}")


if __name__ == "__main__":
    unittest.main()
