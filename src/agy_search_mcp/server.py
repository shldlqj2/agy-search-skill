"""stdio MCP entry point for AGY-backed web search."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from .backend import (
    DEFAULT_MAX_CHARS,
    DEFAULT_MAX_RESULTS,
    MAX_FETCH_CHARS,
    MAX_RESULTS,
    MAX_TIMEOUT_SECONDS,
    AGYRunner,
    AGYSearchError,
    ArtifactStore,
    SearchService,
)


LOGGER = logging.getLogger(__name__)

INSTRUCTIONS = (
    "Use agy_search for current external web research; AGY performs all web search and page reads. "
    "Use agy_fetch only when more content from one returned source is needed. Results include source "
    "provenance and may be partial. Do not assume a generated summary is a verbatim source quote. "
    "Do not use status polling: each call waits for its AGY request to finish."
)


def create_server(service: SearchService | None = None) -> MCPServer:
    """Build a server with injectable state for direct MCP tests."""
    if service is None:
        store = ArtifactStore.from_environment()
        service = SearchService(AGYRunner(store), store)
    mcp = MCPServer("agy-search", instructions=INSTRUCTIONS, version="0.1.0")

    @mcp.tool()
    async def agy_search(
        query: Annotated[str, Field(min_length=1, description="Question or search query to research with AGY.")],
        max_results: Annotated[
            int,
            Field(ge=1, le=MAX_RESULTS, description="Maximum source records to return."),
        ] = DEFAULT_MAX_RESULTS,
        depth: Annotated[
            Literal["quick", "standard", "deep"],
            Field(description="Research depth; standard is the default."),
        ] = "standard",
        domains: Annotated[
            list[str] | None,
            Field(description="Optional hostname allowlist, such as ['docs.python.org']."),
        ] = None,
        language: Annotated[str | None, Field(description="Optional preferred source language.")] = None,
        as_of: Annotated[
            str | None,
            Field(description="Optional freshness date to evaluate, not a historical snapshot."),
        ] = None,
        timeout_seconds: Annotated[
            int | None,
            Field(
                ge=1,
                le=MAX_TIMEOUT_SECONDS,
                description=(
                    "Optional AGY deadline in seconds. If omitted, quick uses 180, "
                    "standard uses 300, and deep uses 600 seconds."
                ),
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Search the live web through AGY and return only sources AGY opened in this run."""
        try:
            return await service.search(
                query=query,
                max_results=max_results,
                depth=depth,
                domains=domains,
                language=language,
                as_of=as_of,
                timeout_seconds=timeout_seconds,
            )
        except AGYSearchError as exc:
            LOGGER.warning("AGY search failed: %s", exc.code)
            return exc.as_dict()

    @mcp.tool()
    async def agy_fetch(
        url: Annotated[str | None, Field(description="Exact http(s) URL to read through AGY.")] = None,
        source_id: Annotated[
            str | None,
            Field(description="A source_id returned by agy_search in this local server session."),
        ] = None,
        focus: Annotated[str | None, Field(description="Optional topic or passage to prioritize.")] = None,
        max_chars: Annotated[
            int,
            Field(ge=200, le=MAX_FETCH_CHARS, description="Maximum content characters to return."),
        ] = DEFAULT_MAX_CHARS,
        timeout_seconds: Annotated[
            int | None,
            Field(
                ge=1,
                le=MAX_TIMEOUT_SECONDS,
                description="Optional AGY deadline in seconds; omitted defaults to 300 seconds.",
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Read one page through AGY; content_kind says whether the source text was an artifact or model extract."""
        try:
            return await service.fetch(
                url=url,
                source_id=source_id,
                focus=focus,
                max_chars=max_chars,
                timeout_seconds=timeout_seconds,
            )
        except AGYSearchError as exc:
            LOGGER.warning("AGY fetch failed: %s", exc.code)
            return exc.as_dict()

    return mcp


mcp = create_server()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
