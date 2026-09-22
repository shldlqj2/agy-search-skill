import asyncio
import tempfile
import unittest
from pathlib import Path

from mcp import Client

from agy_search_mcp.backend import ArtifactStore, RunOutcome, SearchService
from agy_search_mcp.server import create_server


def _tool(name, parameters):
    return {
        "event": "step_update",
        "step_update": {
            "state": "DONE",
            "step_type": "tool",
            "tool_name": name,
            "tool_info": {"name": name, "parameters": parameters},
        },
    }


class _Runner:
    def __init__(self, run_dir):
        self.run_dir = run_dir

    async def run(self, **kwargs):
        structured = {
            "status": "ok",
            "results": [
                {
                    "id": "S1",
                    "title": "Test source",
                    "url": "https://example.test/page",
                    "publisher": "Example",
                    "published_at": None,
                    "summary": "Source-grounded test result.",
                    "evidence_excerpt": "Test excerpt.",
                }
            ],
            "caveats": [],
        }
        terminal = {"status": "SUCCESS", "structured_output": structured}
        return RunOutcome(
            request_id="fixture",
            run_dir=self.run_dir,
            events=[
                _tool("search_web", {"query": "test"}),
                _tool("read_url_content", {"Url": "https://example.test/page"}),
                {"event": "result", "result": terminal},
            ],
            terminal=terminal,
            structured=structured,
            return_code=0,
            stderr="",
        )


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_client_handshake_lists_tools_and_calls_search(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = root / "run"
            run_dir.mkdir()
            service = SearchService(_Runner(run_dir), ArtifactStore(root / "data"))

            async with Client(create_server(service)) as client:
                tools = await client.list_tools()
                result = await client.call_tool("agy_search", {"query": "test", "depth": "quick"})

        self.assertEqual({item.name for item in tools.tools}, {"agy_search", "agy_fetch"})
        self.assertFalse(result.is_error)
        self.assertEqual(result.structured_content["status"], "ok")
        self.assertEqual(len(result.structured_content["results"]), 1)


if __name__ == "__main__":
    unittest.main()
