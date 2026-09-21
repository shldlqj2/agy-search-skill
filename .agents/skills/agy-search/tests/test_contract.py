import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "agy_search.py"
SPEC = importlib.util.spec_from_file_location("agy_search", SCRIPT)
agy_search = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(agy_search)


def tool(name, parameters):
    return {
        "event": "step_update",
        "step_update": {
            "state": "DONE",
            "step_type": "tool",
            "tool_name": name,
            "tool_info": {"name": name, "parameters": parameters},
        },
    }


def init(tools=None):
    return {
        "event": "init",
        "init": {"tools": tools or ["search_web", "read_url_content", "view_file", "finish"]},
    }


def valid_result(url="https://example.org/fact"):
    return {
        "query": "q",
        "searched_at": "2026-09-21",
        "status": "answered",
        "answer": "The fact is supported [S1].",
        "sources": [
            {
                "id": "S1",
                "url": url,
                "title": "Fact",
                "publisher": "Example",
                "published_at": "2026-09-20",
                "source_type": "primary",
                "evidence_excerpt": "The fact is supported.",
            }
        ],
        "claims": [
            {
                "id": "C1",
                "text": "The fact is supported.",
                "source_ids": ["S1"],
                "producer_assessment": "supported",
            }
        ],
        "caveats": [],
    }


class ContractTests(unittest.TestCase):
    def test_valid_trace_passes(self):
        events = [
            init(),
            tool("search_web", {"query": "q"}),
            tool("read_url_content", {"Url": "https://example.org/fact"}),
        ]
        audit = agy_search.audit_result(valid_result(), events, 0, {"status": "SUCCESS"})
        self.assertTrue(audit["passed"])

    def test_declared_but_unread_url_fails(self):
        events = [
            init(),
            tool("search_web", {"query": "q"}),
            tool("read_url_content", {"Url": "https://example.org/other"}),
        ]
        audit = agy_search.audit_result(valid_result(), events, 0, {"status": "SUCCESS"})
        self.assertFalse(audit["passed"])
        failed = {item["name"] for item in audit["checks"] if not item["passed"]}
        self.assertIn("all_sources_were_read", failed)

    def test_closed_book_answer_fails(self):
        audit = agy_search.audit_result(valid_result(), [init()], 0, {"status": "SUCCESS"})
        self.assertFalse(audit["passed"])
        failed = {item["name"] for item in audit["checks"] if not item["passed"]}
        self.assertIn("search_executed", failed)
        self.assertIn("url_read_executed", failed)

    def test_unknown_source_id_fails(self):
        result = valid_result()
        result["claims"][0]["source_ids"] = ["S9"]
        events = [
            init(),
            tool("search_web", {"query": "q"}),
            tool("read_url_content", {"Url": "https://example.org/fact"}),
        ]
        audit = agy_search.audit_result(result, events, 0, {"status": "SUCCESS"})
        self.assertFalse(audit["passed"])
        failed = {item["name"] for item in audit["checks"] if not item["passed"]}
        self.assertIn("claim_source_ids_exist", failed)

    def test_answered_without_inline_citation_fails(self):
        result = valid_result()
        result["answer"] = "The fact is supported."
        events = [
            init(),
            tool("search_web", {"query": "q"}),
            tool("read_url_content", {"Url": "https://example.org/fact"}),
        ]
        audit = agy_search.audit_result(result, events, 0, {"status": "SUCCESS"})
        self.assertFalse(audit["passed"])
        failed = {item["name"] for item in audit["checks"] if not item["passed"]}
        self.assertIn("answer_has_citations_when_answered", failed)

    def test_combined_citation_group_is_parsed(self):
        result = valid_result()
        result["sources"].append(
            {
                "id": "S2",
                "url": "https://example.org/second",
                "title": "Second",
                "publisher": "Example",
                "published_at": "2026-09-20",
                "source_type": "secondary",
                "evidence_excerpt": "Additional support.",
            }
        )
        result["claims"][0]["source_ids"] = ["S1", "S2"]
        result["answer"] = "The fact is supported [S1, S2]."
        events = [
            init(),
            tool("search_web", {"query": "q"}),
            tool("read_url_content", {"Url": "https://example.org/fact"}),
            tool("read_url_content", {"Url": "https://example.org/second"}),
        ]
        audit = agy_search.audit_result(result, events, 0, {"status": "SUCCESS"})
        self.assertTrue(audit["passed"])
        answer_check = next(
            item for item in audit["checks"] if item["name"] == "answer_has_citations_when_answered"
        )
        self.assertIn("S1", answer_check["evidence"])
        self.assertIn("S2", answer_check["evidence"])

    def test_dangerous_tool_exposure_is_reported_but_use_fails(self):
        events = [
            init(["search_web", "read_url_content", "run_command"]),
            tool("search_web", {"query": "q"}),
            tool("read_url_content", {"Url": "https://example.org/fact"}),
        ]
        audit = agy_search.audit_result(valid_result(), events, 0, {"status": "SUCCESS"})
        self.assertTrue(audit["passed"])
        warning = next(item for item in audit["checks"] if item["name"] == "dangerous_tools_exposed")
        self.assertFalse(warning["passed"])
        self.assertFalse(warning["blocking"])

        events.append(tool("run_command", {"CommandLine": "curl https://example.org"}))
        audit = agy_search.audit_result(valid_result(), events, 0, {"status": "SUCCESS"})
        self.assertFalse(audit["passed"])
        failed = {item["name"] for item in audit["checks"] if not item["passed"]}
        self.assertIn("no_dangerous_tools_used", failed)


if __name__ == "__main__":
    unittest.main()
