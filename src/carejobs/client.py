"""Client for the CareJobs.Now healthcare jobs API (a remote MCP server, no key needed).

Standard library only. Every method returns a :class:`Result`, a plain ``dict`` of the
tool's structured data that also carries the server's readable summary as ``.text``.
"""

from __future__ import annotations

import http.client
import json
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from ._version import __version__
from .types import Care, EmployerType, Kind, Sort

DEFAULT_BASE_URL = "https://carejobs.now"
DEFAULT_TIMEOUT = 30.0


class CareJobsError(Exception):
    """Every failure of the client.

    ``code`` says where it came from:

    * ``"tool"``: the server ran the tool and answered with an error (unknown kind,
      unknown employer). ``str(error)`` is the server's explanation.
    * ``"rpc"``: a JSON-RPC error (``rpc_code`` is set).
    * ``"http"``: a non-2xx HTTP status (``status`` is set).
    * ``"network"``: the request never completed.
    * ``"timeout"``: no answer within ``timeout`` seconds.
    * ``"protocol"``: the answer was not the shape the MCP protocol promises.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status: Optional[int] = None,
        tool: Optional[str] = None,
        rpc_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.tool = tool
        self.rpc_code = rpc_code


class Result(Dict[str, Any]):
    """A ``dict`` of a tool's structured data, plus the readable summary as ``.text``."""

    text: str

    def __init__(self, data: Dict[str, Any], text: str) -> None:
        super().__init__(data)
        self.text = text


def _drop_none(arguments: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in arguments.items() if value is not None}


def _parse_body(body: str, content_type: str, request_id: int) -> Dict[str, Any]:
    """Read the JSON-RPC message out of a plain JSON body or a text/event-stream body."""
    if "text/event-stream" in content_type:
        fallback: Optional[Dict[str, Any]] = None
        for event in body.replace("\r\n", "\n").split("\n\n"):
            data_lines = [
                line[5:][1:] if line[5:].startswith(" ") else line[5:]
                for line in event.split("\n")
                if line.startswith("data:")
            ]
            if not data_lines:
                continue
            try:
                message = json.loads("\n".join(data_lines))
            except ValueError:
                continue
            if not isinstance(message, dict):
                continue
            if message.get("id") == request_id:
                return message
            if fallback is None and ("result" in message or "error" in message):
                fallback = message
        if fallback is not None:
            return fallback
        raise CareJobsError("The event stream held no JSON-RPC answer", code="protocol")
    try:
        message = json.loads(body)
    except ValueError as error:
        raise CareJobsError("The server did not answer with JSON", code="protocol") from error
    if not isinstance(message, dict):
        raise CareJobsError("The server did not answer with a JSON-RPC object", code="protocol")
    return message


class CareJobs:
    """Search US healthcare jobs and the pay employers post.

    :param base_url: default ``https://carejobs.now``. The MCP endpoint is ``<base_url>/api/mcp``.
    :param timeout: give up on a request after this many seconds (default 30).
    :param user_agent: sent as the User-Agent header (default ``carejobs-python/<version>``).
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent or f"carejobs-python/{__version__}"
        self._next_id = 1

    # -- the six tools -------------------------------------------------------

    def search_jobs(
        self,
        query: Optional[str] = None,
        *,
        kind: Optional[Kind] = None,
        employer: Optional[str] = None,
        state: Optional[str] = None,
        remote: Optional[bool] = None,
        min_hourly_usd: Optional[int] = None,
        sort: Optional[Sort] = None,
        limit: Optional[int] = None,
    ) -> Result:
        """Search open healthcare jobs. Every filter is optional.

        ``query``: words every job must carry in its title, place, department or schedule.
        ``employer``: an employer slug (``kaiser-permanente``) or name. ``state``: ``TX`` or
        ``Texas``. ``min_hourly_usd``: 1 to 1000. ``limit``: 1 to 25 (default 10).
        Returns ``total``, ``pay``, ``jobs``, ``more``.
        """
        return self.call_tool(
            "search_healthcare_jobs",
            {
                "query": query,
                "kind": kind,
                "employer": employer,
                "state": state,
                "remote": remote,
                "min_hourly_usd": min_hourly_usd,
                "sort": sort,
                "limit": limit,
            },
        )

    def get_pay(self, kind: Optional[Kind] = None, employer: Optional[str] = None) -> Result:
        """What healthcare jobs post as hourly pay.

        No arguments: every kind of job. ``kind``: that job's pay and the employers posting the
        most for it. ``employer``: its pay overall and by kind. Both: that employer's pay for
        that kind.
        """
        return self.call_tool("get_healthcare_pay", {"kind": kind, "employer": employer})

    def get_job_market(self) -> Result:
        """How many healthcare jobs are open, by kind of job, state and employer."""
        return self.call_tool("get_healthcare_job_market", {})

    def get_jobs_by_state(
        self,
        state: Optional[str] = None,
        kind: Optional[Kind] = None,
        limit: Optional[int] = None,
    ) -> Result:
        """Open jobs by state.

        No state: every state. A state: its jobs by kind, pay, towns, employers and newest jobs.
        A state and a ``kind``: the same for that kind (``kind`` needs a state). ``limit``
        (1 to 25) is how many of the newest jobs to return.
        """
        return self.call_tool(
            "get_healthcare_jobs_by_state", {"state": state, "kind": kind, "limit": limit}
        )

    def list_employers(
        self,
        query: Optional[str] = None,
        *,
        type: Optional[EmployerType] = None,
        care: Optional[Care] = None,
        state: Optional[str] = None,
        kind: Optional[Kind] = None,
        limit: Optional[int] = None,
    ) -> Result:
        """Employers (and AI-training programs and job boards), most open jobs first.

        ``query``: part of the name. ``type``: ``employer``, ``ai-program`` or ``job-board``.
        ``care``: kind of care. ``state`` / ``kind``: only those with open jobs there or of that
        kind. ``limit``: 1 to 100 (default 20).
        """
        return self.call_tool(
            "list_healthcare_employers",
            {
                "query": query,
                "type": type,
                "care": care,
                "state": state,
                "kind": kind,
                "limit": limit,
            },
        )

    def get_employer(self, slug: str) -> Result:
        """One employer by slug (``kaiser-permanente``) or name."""
        return self.call_tool("get_healthcare_employer", {"employer": slug})

    # -- low level -------------------------------------------------------------

    def list_tools(self) -> List[Dict[str, Any]]:
        """The tools the server offers, with their input schemas."""
        result = self._rpc("tools/list", {})
        tools = result.get("tools") if isinstance(result, dict) else None
        if not isinstance(tools, list):
            raise CareJobsError("tools/list answered without a tools list", code="protocol")
        return tools

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Result:
        """Call any tool by name. ``None`` arguments are left out. The methods above use this."""
        raw = self._rpc(
            "tools/call", {"name": name, "arguments": _drop_none(arguments or {})}, tool=name
        )
        if not isinstance(raw, dict):
            raise CareJobsError(f"{name} answered without a result", code="protocol", tool=name)
        parts = raw.get("content")
        text = "\n".join(
            part["text"]
            for part in (parts if isinstance(parts, list) else [])
            if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)
        )
        if raw.get("isError"):
            raise CareJobsError(text or f"{name} failed", code="tool", tool=name)
        data = raw.get("structuredContent")
        if not isinstance(data, dict):
            raise CareJobsError(
                f"{name} answered without structured content", code="protocol", tool=name
            )
        return Result(data, text)

    # -- transport -------------------------------------------------------------

    def _rpc(self, method: str, params: Dict[str, Any], tool: Optional[str] = None) -> Any:
        request_id = self._next_id
        self._next_id += 1
        url = f"{self.base_url}/api/mcp"
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": self.user_agent,
            },
        )
        status = 200
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as error:
            status = error.code
            content_type = error.headers.get("Content-Type", "") if error.headers else ""
            body = error.read().decode("utf-8", errors="replace")
            detail = f"HTTP {status}"
            try:
                message = _parse_body(body, content_type, request_id)
                rpc_error = message.get("error")
                if isinstance(rpc_error, dict) and rpc_error.get("message"):
                    detail += f": {rpc_error['message']}"
            except CareJobsError:
                if body.strip():
                    detail += f": {body.strip()[:200]}"
            raise CareJobsError(detail, code="http", status=status, tool=tool) from None
        except (socket.timeout, TimeoutError) as error:
            raise CareJobsError(
                f"No answer from {url} within {self.timeout:g} s", code="timeout", tool=tool
            ) from error
        except urllib.error.URLError as error:
            if isinstance(error.reason, (socket.timeout, TimeoutError)):
                raise CareJobsError(
                    f"No answer from {url} within {self.timeout:g} s", code="timeout", tool=tool
                ) from error
            raise CareJobsError(
                f"Could not reach {url}: {error.reason}", code="network", tool=tool
            ) from error
        except (OSError, http.client.HTTPException) as error:
            raise CareJobsError(f"Could not reach {url}: {error}", code="network", tool=tool) from error

        message = _parse_body(body, content_type, request_id)
        rpc_error = message.get("error")
        if rpc_error is not None:
            if not isinstance(rpc_error, dict):
                raise CareJobsError("Malformed JSON-RPC error", code="protocol", tool=tool)
            raise CareJobsError(
                str(rpc_error.get("message") or "JSON-RPC error"),
                code="rpc",
                rpc_code=rpc_error.get("code") if isinstance(rpc_error.get("code"), int) else None,
                tool=tool,
            )
        return message.get("result")
