"""Live tests: these call https://carejobs.now/api/mcp (free, no key)."""

import re
import unittest
from pathlib import Path

import carejobs
from carejobs import CARE_TYPES, EMPLOYER_TYPES, KINDS, SORTS, CareJobs, CareJobsError


class LiveClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cj = CareJobs(timeout=60)

    def test_version_matches_pyproject(self):
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if not pyproject.exists():
            self.skipTest("pyproject.toml is not next to the tests")
        match = re.search(r'^version = "([^"]+)"', pyproject.read_text(encoding="utf-8"), re.M)
        self.assertEqual(carejobs.__version__, match.group(1))

    def test_search_jobs_returns_dict_and_text(self):
        result = self.cj.search_jobs(limit=2)
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result.text, str)
        self.assertTrue(result.text)
        self.assertGreater(result["total"], 0)
        self.assertTrue(1 <= len(result["jobs"]) <= 2)
        job = result["jobs"][0]
        self.assertIsInstance(job["title"], str)
        self.assertIsInstance(job["schedule"], list)
        self.assertTrue(job["url"].startswith("https://carejobs.now/jobs/"))

    def test_search_jobs_filters(self):
        result = self.cj.search_jobs("icu", kind="nurses", state="TX", limit=2)
        self.assertLessEqual(len(result["jobs"]), 2)
        for job in result["jobs"]:
            self.assertTrue(job["location"].endswith("TX"), job["location"])

    def test_get_pay(self):
        overview = self.cj.get_pay()
        self.assertTrue(overview["pay_by_kind"])
        nurses = self.cj.get_pay(kind="nurses")
        self.assertEqual(nurses["kind"], "nurses")
        self.assertGreater(nurses["pay"]["median"], 0)
        self.assertTrue(nurses["best_paying"])
        self.assertIsInstance(nurses.text, str)

    def test_get_job_market(self):
        market = self.cj.get_job_market()
        self.assertGreater(market["open_jobs"], 1000)
        self.assertTrue(any(state["code"] == "TX" for state in market["open_by_state"]))

    def test_get_jobs_by_state(self):
        self.assertGreaterEqual(len(self.cj.get_jobs_by_state()["states"]), 50)
        texas = self.cj.get_jobs_by_state("TX", limit=2)
        self.assertEqual(texas["state"], "TX")
        self.assertLessEqual(len(texas["newest"]), 2)
        self.assertEqual(self.cj.get_jobs_by_state("TX", kind="nurses", limit=1)["kind"], "nurses")

    def test_list_employers_and_get_employer(self):
        listing = self.cj.list_employers("kaiser", limit=3)
        self.assertTrue(any(entry["slug"] == "kaiser-permanente" for entry in listing["entries"]))
        employer = self.cj.get_employer("kaiser-permanente")
        self.assertEqual(employer["slug"], "kaiser-permanente")
        self.assertGreater(employer["open_jobs"], 0)

    def test_tool_error(self):
        with self.assertRaises(CareJobsError) as caught:
            self.cj.get_pay(kind="registered-nurse")
        self.assertEqual(caught.exception.code, "tool")
        self.assertEqual(caught.exception.tool, "get_healthcare_pay")
        self.assertIn("Unknown kind", str(caught.exception))
        with self.assertRaises(CareJobsError) as caught:
            self.cj.get_employer("no-such-employer-xyz")
        self.assertEqual(caught.exception.code, "tool")

    def test_unknown_tool_is_rpc_error(self):
        with self.assertRaises(CareJobsError) as caught:
            self.cj.call_tool("no_such_tool")
        self.assertEqual(caught.exception.code, "rpc")

    def test_enums_match_live_tools_list(self):
        tools = {tool["name"]: tool for tool in self.cj.list_tools()}
        self.assertEqual(
            sorted(tools),
            [
                "get_healthcare_employer",
                "get_healthcare_job_market",
                "get_healthcare_jobs_by_state",
                "get_healthcare_pay",
                "list_healthcare_employers",
                "search_healthcare_jobs",
            ],
        )

        def props(name):
            return tools[name]["inputSchema"]["properties"]

        for name in (
            "search_healthcare_jobs",
            "get_healthcare_pay",
            "get_healthcare_jobs_by_state",
            "list_healthcare_employers",
        ):
            self.assertEqual(props(name)["kind"]["enum"], list(KINDS), name)
        self.assertEqual(props("search_healthcare_jobs")["sort"]["enum"], list(SORTS))
        self.assertEqual(props("list_healthcare_employers")["care"]["enum"], list(CARE_TYPES))
        self.assertEqual(props("list_healthcare_employers")["type"]["enum"], list(EMPLOYER_TYPES))


if __name__ == "__main__":
    unittest.main()
