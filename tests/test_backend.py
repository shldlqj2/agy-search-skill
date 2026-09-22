import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

from agy_search_mcp.backend import (
    AGYSearchError,
    AGYRunner,
    ArtifactStore,
    RunOutcome,
    SearchService,
    display_text,
    search_timeout,
)


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


def outcome(run_dir, structured, *calls):
    events = [*calls, {"event": "result", "result": {"status": "SUCCESS", "structured_output": structured}}]
    return RunOutcome(
        request_id="fixture",
        run_dir=run_dir,
        events=events,
        terminal=events[-1]["result"],
        structured=structured,
        return_code=0,
        stderr="",
    )


class FakeRunner:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    async def run(self, **kwargs):
        self.calls.append(kwargs)
        return self.outcomes.pop(0)


class BlockingRunner(FakeRunner):
    def __init__(self, outcomes):
        super().__init__(outcomes)
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def run(self, **kwargs):
        self.calls.append(kwargs)
        self.entered.set()
        await self.release.wait()
        return self.outcomes.pop(0)


class BackendTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = ArtifactStore(self.root / "data")

    def tearDown(self):
        self.temp_dir.cleanup()

    def valid_search(self):
        return {
            "status": "ok",
            "results": [
                {
                    "id": "S1",
                    "title": "Official fact",
                    "url": "https://docs.example.test/fact",
                    "publisher": "Example",
                    "published_at": None,
                    "summary": "A source-grounded summary.",
                    "evidence_excerpt": "A short source excerpt.",
                }
            ],
            "caveats": [],
        }

    def valid_search_outcome(self):
        run_dir = self.root / "search-run"
        run_dir.mkdir()
        return outcome(
            run_dir,
            self.valid_search(),
            tool("search_web", {"query": "fact"}),
            tool("read_url_content", {"Url": "https://docs.example.test/fact"}),
        )

    def valid_fetch_outcome(self):
        run_dir = self.root / "fetch-run"
        run_dir.mkdir()
        return outcome(
            run_dir,
            {
                "status": "ok",
                "url": "https://untrusted.example.test/redirected",
                "title": "Fact page",
                "summary": "A summary.",
                "evidence_excerpt": "An excerpt.",
                "fallback_extract": "Generated fallback extract.",
                "caveats": [],
            },
            tool("read_url_content", {"Url": "https://docs.example.test/fact"}),
        )

    def test_timeout_policy_is_finite_and_adaptive(self):
        self.assertEqual(search_timeout("quick", None), 180)
        self.assertEqual(search_timeout("standard", None), 300)
        self.assertEqual(search_timeout("deep", None), 600)
        self.assertEqual(search_timeout("deep", 42), 42)
        with self.assertRaises(AGYSearchError):
            search_timeout("standard", 601)

    def test_display_fields_strip_html_without_claiming_new_source_content(self):
        self.assertEqual(
            display_text('<li><a href="/release">Latest Python 3 Release</a></li>'),
            "Latest Python 3 Release",
        )

    async def test_search_returns_only_read_sources_and_records_adaptive_timeout(self):
        runner = FakeRunner([self.valid_search_outcome()])
        service = SearchService(runner, self.store)

        result = await service.search(query="  fact  ", depth="deep", domains=["example.test"])

        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["read_status"], "read")
        self.assertEqual(runner.calls[0]["timeout_seconds"], 600)
        self.assertIn("Only return sources", runner.calls[0]["prompt"])
        self.assertTrue(self.store.resolve_source(result["results"][0]["source_id"]))

    async def test_fetch_preserves_requested_url_and_labels_model_fallback(self):
        runner = FakeRunner([self.valid_search_outcome(), self.valid_fetch_outcome()])
        service = SearchService(runner, self.store)
        search = await service.search(query="fact")

        result = await service.fetch(source_id=search["results"][0]["source_id"])

        self.assertEqual(result["url"], "https://docs.example.test/fact")
        self.assertEqual(result["content"], "Generated fallback extract.")
        self.assertEqual(result["content_kind"], "agy_generated_extract")
        self.assertIn("Do not use search_web", runner.calls[1]["prompt"])

    async def test_concurrent_request_is_rejected_instead_of_waiting_or_polling(self):
        runner = BlockingRunner([self.valid_search_outcome()])
        service = SearchService(runner, self.store)
        first = asyncio.create_task(service.search(query="fact"))
        await runner.entered.wait()

        with self.assertRaisesRegex(AGYSearchError, "already running"):
            await service.search(query="second fact")

        runner.release.set()
        await first

    async def test_dangerous_tool_use_fails_the_provenance_gate(self):
        run_dir = self.root / "unsafe-run"
        run_dir.mkdir()
        unsafe = outcome(
            run_dir,
            self.valid_search(),
            tool("search_web", {"query": "fact"}),
            tool("read_url_content", {"Url": "https://docs.example.test/fact"}),
            tool("browser_subagent", {"task": "do not do this"}),
        )
        service = SearchService(FakeRunner([unsafe]), self.store)

        with self.assertRaisesRegex(AGYSearchError, "provenance"):
            await service.search(query="fact")

    async def test_cancelling_a_runner_terminates_the_child_and_preserves_trace_metadata(self):
        fake_agy = self.root / "fake-agy"
        fake_agy.write_text(
            f"#!{sys.executable}\n"
            "import json\n"
            "import time\n"
            "print(json.dumps({'event': 'init', 'conversation_id': 'fixture'}), flush=True)\n"
            "time.sleep(60)\n",
            encoding="utf-8",
        )
        fake_agy.chmod(0o755)
        runner = AGYRunner(self.store, agy_path=str(fake_agy))
        task = asyncio.create_task(
            runner.run(
                request_id="cancelled",
                prompt="fixture",
                schema={"type": "object"},
                timeout_seconds=10,
                effort="low",
            )
        )
        trace_path = self.store.runs_dir / "cancelled" / "trace.ndjson"
        for _ in range(100):
            if trace_path.exists() and trace_path.stat().st_size:
                break
            await asyncio.sleep(0.01)
        else:
            self.fail("fake AGY did not start")

        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

        metadata = json.loads((self.store.runs_dir / "cancelled" / "run.json").read_text())
        self.assertTrue(metadata["cancelled"])
        self.assertIsNotNone(metadata["return_code"])
        self.assertTrue(trace_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    unittest.main()
