"""wes_explain_run_failure asks NGS360 for the diagnosis; it never talks to AWS."""

import asyncio

import httpx
from mcp.server.fastmcp import FastMCP

from ngs360_mcp_server.client import NGS360Client
from ngs360_mcp_server.tools.wes import register_wes_tools


def test_tool_calls_the_diagnosis_endpoint_with_the_users_token():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"run_id": "r1", "available": True, "failure_reason": "X"})

    client = NGS360Client(base_url="http://ngs360.test", token="user-key", path_prefix="/ga4gh/wes/v1")
    client._client = httpx.AsyncClient(base_url="http://ngs360.test", transport=httpx.MockTransport(handler))
    mcp = FastMCP("t")
    register_wes_tools(mcp, client)

    names = [t.name for t in asyncio.run(mcp.list_tools())]
    assert "wes_explain_run_failure" in names

    result = asyncio.run(mcp.call_tool("wes_explain_run_failure", {"run_id": "r1"}))
    assert seen["path"] == "/ga4gh/wes/v1/runs/r1/diagnosis"
    assert seen["auth"] == "Bearer user-key"
    assert "failure_reason" in str(result)
