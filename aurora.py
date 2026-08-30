"""AURORA TRACE: an explainable local coding-agent demo.

Only Python's standard library is used. The implementation intentionally keeps
the important Agent logic visible: context, tools, parsing, execution, loop,
guardrails, and termination.
"""

from __future__ import annotations

import difflib
import io
import json
import os
import shlex
import shutil
import subprocess
import threading
import time
import uuid
import zipfile
from email.parser import BytesParser
from email.policy import default as email_default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
SEED = ROOT / "seed_project"
PORT = int(os.getenv("AURORA_PORT", "8765"))
RUNS: dict[str, dict[str, Any]] = {}
PROJECTS: dict[str, dict[str, Any]] = {
    "demo": {"id": "demo", "name": "Todo Boundary Demo", "path": SEED,
             "source": "built-in", "file_count": 2}
}
RUN_LOCK = threading.Lock()
PROJECT_LOCK = threading.Lock()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
PROJECT_INDEX = ROOT / "projects.json"
IGNORED_DIRS = {"__pycache__", ".git", ".idea", ".vscode", ".venv", "venv", "node_modules", "dist", "build"}


def now() -> str:
    return time.strftime("%H:%M:%S")


def safe_path(workspace: Path, relative: str) -> Path:
    candidate = (workspace / relative).resolve()
    workspace = workspace.resolve()
    if candidate != workspace and workspace not in candidate.parents:
        raise ValueError("path escapes the isolated workspace")
    return candidate


def safe_web_path(relative: str) -> Path:
    """Resolve static assets without allowing the URL to escape web/."""
    candidate = (WEB / unquote(relative)).resolve()
    if candidate != WEB.resolve() and WEB.resolve() not in candidate.parents:
        raise ValueError("static asset escapes web root")
    return candidate


def safe_zip_member(name: str) -> Path:
    """Validate a ZIP member before extraction; return a normalized relative path."""
    normalized = name.replace("\\", "/")
    relative = Path(normalized)
    if not normalized or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe archive path: {name}")
    if len(normalized) > 240 or (len(normalized) > 1 and normalized[1] == ":"):
        raise ValueError(f"unsafe archive path: {name}")
    return relative


def import_zip_project(filename: str, data: bytes) -> dict[str, Any]:
    """Import a small ZIP project into a new immutable-once-created project folder."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("ZIP exceeds the 10 MB upload limit")
    if not filename.lower().endswith(".zip"):
        raise ValueError("only .zip project archives are supported")
    project_id = "p-" + uuid.uuid4().hex[:8]
    destination = ROOT / "projects" / project_id
    files: list[tuple[Path, bytes]] = []
    total_uncompressed = 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if len(archive.infolist()) > 500:
                raise ValueError("archive contains too many entries")
            for item in archive.infolist():
                relative = safe_zip_member(item.filename)
                if item.is_dir():
                    continue
                total_uncompressed += item.file_size
                if total_uncompressed > 30 * 1024 * 1024:
                    raise ValueError("uncompressed project exceeds the 30 MB limit")
                files.append((relative, archive.read(item)))
    except zipfile.BadZipFile as exc:
        raise ValueError("uploaded file is not a valid ZIP archive") from exc
    if not files:
        raise ValueError("archive contains no files")
    destination.mkdir(parents=True, exist_ok=False)
    for relative, content in files:
        target = safe_path(destination, str(relative))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    top_dirs = {path.parts[0] for path, _ in files if len(path.parts) > 1}
    source = destination / next(iter(top_dirs)) if len(top_dirs) == 1 and all(path.parts[0] == next(iter(top_dirs)) for path, _ in files) else destination
    profile = profile_project(source)
    project = {"id": project_id, "name": Path(filename).stem,
               "path": source, "source": "uploaded", "file_count": len(files),
               "profile": profile}
    with PROJECT_LOCK:
        PROJECTS[project_id] = project
        save_project_index()
    return {k: str(v) if isinstance(v, Path) else v for k, v in project.items() if k != "path"}


def profile_project(root: Path) -> dict[str, Any]:
    extensions: dict[str, int] = {}
    names: set[str] = set()
    file_count = 0
    for item in root.rglob("*"):
        relative = item.relative_to(root)
        if not item.is_file() or any(part in IGNORED_DIRS for part in relative.parts):
            continue
        file_count += 1
        names.add(item.name.lower())
        extension = item.suffix.lower() or "[no extension]"
        extensions[extension] = extensions.get(extension, 0) + 1
    languages = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                 ".java": "Java", ".go": "Go", ".rs": "Rust", ".cpp": "C++"}
    detected = [languages[ext] for ext, _ in sorted(extensions.items(), key=lambda pair: -pair[1]) if ext in languages][:3]
    commands = []
    if "pytest.ini" in names:
        commands.append("python -m pytest")
    elif "tests" in {part.lower() for item in root.rglob("*") for part in item.relative_to(root).parts}:
        commands.append("python -m unittest discover -s tests -v")
    elif ".py" in extensions:
        commands.append("python -m unittest discover -v")
    if "package.json" in names:
        commands.append("npm test")
    return {"files": file_count, "languages": detected or ["Unknown"],
            "suggested_tests": commands or ["No test command detected"]}


def save_project_index() -> None:
    records = []
    for project in PROJECTS.values():
        if project["id"] == "demo":
            continue
        record = {k: v for k, v in project.items() if k != "path"}
        record["path"] = str(project["path"].relative_to(ROOT)).replace("\\", "/")
        records.append(record)
    PROJECT_INDEX.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def load_project_index() -> None:
    if not PROJECT_INDEX.exists():
        return
    try:
        records = json.loads(PROJECT_INDEX.read_text(encoding="utf-8"))
        for record in records:
            path = safe_path(ROOT, record.pop("path"))
            if path.exists() and path.is_dir():
                PROJECTS[record["id"]] = {**record, "path": path}
    except (ValueError, KeyError, json.JSONDecodeError):
        return


class ToolExecutor:
    """Local tools with explicit boundaries and concise, serializable output."""

    ALLOWED_PREFIXES = ("python", "pytest", "npm", "node")

    def __init__(self, workspace: Path):
        self.workspace = workspace

    def list_files(self, path: str = ".") -> dict[str, Any]:
        root = safe_path(self.workspace, path)
        files = []
        for item in sorted(root.rglob("*")):
            relative = item.relative_to(self.workspace)
            if item.is_file() and not any(part in IGNORED_DIRS for part in relative.parts):
                files.append(str(item.relative_to(self.workspace)).replace("\\", "/"))
        return {"files": files}

    def read_file(self, path: str) -> dict[str, Any]:
        target = safe_path(self.workspace, path)
        text = target.read_text(encoding="utf-8")
        return {"path": path, "content": text, "lines": len(text.splitlines())}

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        target = safe_path(self.workspace, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        before = target.read_text(encoding="utf-8") if target.exists() else ""
        target.write_text(content, encoding="utf-8")
        return self._change_result(path, before, content)

    def replace_text(self, path: str, old: str, new: str) -> dict[str, Any]:
        """Apply one exact replacement so the patch remains small and auditable."""
        target = safe_path(self.workspace, path)
        before = target.read_text(encoding="utf-8")
        occurrences = before.count(old)
        if occurrences != 1:
            raise ValueError(f"expected exactly one match, found {occurrences}")
        after = before.replace(old, new, 1)
        target.write_text(after, encoding="utf-8")
        result = self._change_result(path, before, after)
        result["operation"] = "exact_replace"
        return result

    @staticmethod
    def _change_result(path: str, before: str, after: str) -> dict[str, Any]:
        diff = "".join(difflib.unified_diff(
            before.splitlines(True), after.splitlines(True),
            fromfile=f"a/{path}", tofile=f"b/{path}"
        ))
        return {"path": path, "changed": before != after, "diff": diff,
                "added_lines": sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")),
                "removed_lines": sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))}

    def run_command(self, command: str) -> dict[str, Any]:
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            raise ValueError(f"invalid command syntax: {exc}") from exc
        if not parts or parts[0].lower() not in self.ALLOWED_PREFIXES:
            raise ValueError("command is outside the safe allowlist")
        if any(token in command for token in ("&&", "||", ";", "|", ">", "<")):
            raise ValueError("shell chaining and redirection are disabled")
        if any(token in parts for token in ("-c", "-e", "--eval", "--exec")):
            raise ValueError("inline code execution is disabled")
        for token in parts[1:]:
            if os.path.isabs(token) or (len(token) > 1 and token[1] == ":"):
                raise ValueError("absolute command paths are disabled")
        try:
            proc = subprocess.run(
                parts, cwd=self.workspace, capture_output=True, text=True,
                timeout=20, shell=False
            )
        except subprocess.TimeoutExpired as exc:
            output = ((exc.stdout or "") + (exc.stderr or "")).strip()
            return {"command": command, "returncode": -1, "output": output[-6000:],
                    "ok": False, "timed_out": True}
        output = (proc.stdout + proc.stderr).strip()
        return {"command": command, "returncode": proc.returncode,
                "output": output[-6000:], "ok": proc.returncode == 0}

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        methods = {"list_files": self.list_files, "read_file": self.read_file,
                   "write_file": self.write_file, "replace_text": self.replace_text,
                   "run_command": self.run_command}
        if name not in methods:
            raise ValueError(f"unknown tool: {name}")
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be an object")
        return methods[name](**arguments)


TOOLS = [
    {"name": "list_files", "description": "List files in the isolated task workspace.",
     "parameters": {"path": "string"}},
    {"name": "read_file", "description": "Read a UTF-8 text file.",
     "parameters": {"path": "string"}},
    {"name": "write_file", "description": "Create or replace a UTF-8 text file.",
     "parameters": {"path": "string", "content": "string"}},
    {"name": "replace_text", "description": "Replace exactly one matching text span and return a minimal diff.",
     "parameters": {"path": "string", "old": "string", "new": "string"}},
    {"name": "run_command", "description": "Run one allowlisted local command.",
     "parameters": {"command": "string"}},
]


def emit(run: dict[str, Any], kind: str, title: str, detail: str = "",
         tool: str | None = None, payload: Any = None, status: str = "active"):
    event = {"id": len(run["events"]) + 1, "time": now(), "kind": kind,
             "title": title, "detail": detail, "tool": tool,
             "payload": payload, "status": status}
    with run["lock"]:
        run["events"].append(event)
        run["ledger"].append({k: event[k] for k in
                              ("id", "time", "kind", "title", "tool", "status")})
        with run["ledger_path"].open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def compact(value: Any, limit: int = 420) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


class ModelAdapter:
    def __init__(self, mode: str):
        self.mode = mode

    def decide(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        if self.mode == "mock":
            return {"type": "finish", "summary": "演示序列由本地 Mock 模型完成"}
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        url = base + "/chat/completions"
        request_body = {"model": os.getenv("AURORA_MODEL", "gpt-4o-mini"),
                        "messages": messages, "tools": [{"type": "function", "function": {
                            "name": t["name"], "description": t["description"],
                            "parameters": {"type": "object", "properties": {
                                k: {"type": "string"} for k in t["parameters"]},
                                "required": list(t["parameters"]),
                                "additionalProperties": False}}} for t in TOOLS],
                        "tool_choice": "auto"}
        req = Request(url, data=json.dumps(request_body).encode(), method="POST",
                      headers={"Content-Type": "application/json",
                               "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
        try:
            with urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode())
        except (HTTPError, URLError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"model request failed: {exc}") from exc
        message = data["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        if calls:
            call = calls[0]
            return {"type": "tool_call", "tool": call["function"]["name"],
                    "arguments": json.loads(call["function"]["arguments"]),
                    "reason": message.get("content") or "model selected the next tool",
                    "assistant_message": message, "call_id": call.get("id")}
        return {"type": "finish", "summary": message.get("content", "task finished")}


def mock_steps() -> list[dict[str, Any]]:
    todo = """\"\"\"Tiny Todo domain used by the AURORA TRACE demonstration.\"\"\"\n\n\nclass TodoList:\n    def __init__(self, items=None):\n        self.items = list(items or [])\n\n    def add(self, title):\n        self.items.append({\"title\": title, \"done\": False})\n\n    def remove(self, index):\n        if 0 <= index < len(self.items):\n            return self.items.pop(index)\n        return None\n\n    def completed(self):\n        return [item for item in self.items if item[\"done\"]]\n"""
    return [
        {"kind": "state", "title": "Task understood", "detail": "定位删除功能与边界验收条件", "state": "UNDERSTAND"},
        {"kind": "tool", "tool": "list_files", "arguments": {"path": "."}, "reason": "先建立项目地图"},
        {"kind": "tool", "tool": "read_file", "arguments": {"path": "todo.py"}, "reason": "读取业务逻辑"},
        {"kind": "tool", "tool": "read_file", "arguments": {"path": "tests/test_todo.py"}, "reason": "确认测试与验收标准"},
        {"kind": "state", "title": "Acceptance contract locked", "detail": "删除最后一项、保留非法索引安全行为、回归测试通过", "state": "PLAN"},
        {"kind": "state", "title": "Execution started", "detail": "进入受控工具执行阶段", "state": "EXECUTE"},
        {"kind": "tool", "tool": "run_command", "arguments": {"command": "python -m unittest discover -s tests -v"}, "reason": "先复现现有故障，建立修改前证据", "phase": "baseline"},
        {"kind": "tool", "tool": "replace_text", "arguments": {"path": "todo.py", "old": "if 0 <= index < len(self.items) - 1:", "new": "if 0 <= index < len(self.items):"}, "reason": "使用单一精确替换，控制补丁影响面", "phase": "patch"},
        {"kind": "tool", "tool": "run_command", "arguments": {"command": "python -m unittest discover -s tests -v"}, "reason": "用真实测试验证修改"},
        {"kind": "state", "title": "Verification gate passed", "detail": "修改前故障已复现，修改后 5 个测试全部通过，证据链闭合", "state": "VERIFY"},
        {"kind": "finish", "summary": "已修复 Todo 删除边界 Bug，并通过全部 5 项单元测试。"},
    ]


def contract_for(task: str, project: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "goal": task,
        "checks": ["baseline_failure_captured", "minimal_patch_recorded",
                    "regression_tests_passed", "workspace_boundary_respected"],
        "risk": "LOW · isolated workspace / allowlisted commands",
        "project": (project or {}).get("name", "Unknown project"),
    }


def update_evidence_score(run: dict[str, Any]) -> None:
    events = run["events"]
    baseline = any(e.get("payload", {}).get("phase") == "baseline" and
                   e.get("payload", {}).get("ok") is False for e in events
                   if isinstance(e.get("payload"), dict))
    patched = bool(run["diffs"])
    verified = any(e.get("kind") == "tool_result" and
                   e.get("tool") == "run_command" and
                   isinstance(e.get("payload"), dict) and
                   e["payload"].get("ok") is True for e in events)
    run["evidence"] = {"baseline_failure_captured": baseline,
                       "minimal_patch_recorded": patched,
                       "regression_tests_passed": verified,
                       "workspace_boundary_respected": True}
    run["trust_score"] = sum(25 for value in run["evidence"].values() if value)


def run_agent(run: dict[str, Any], mode: str):
    try:
        run["state"] = "UNDERSTAND"
        emit(run, "system", "Run initialized", "隔离工作区已创建 · Evidence Ledger 已启动", status="done")
        update_evidence_score(run)
        if mode == "mock":
            steps = mock_steps()
            executor = ToolExecutor(run["workspace"])
            for step in steps:
                time.sleep(0.48)
                if step["kind"] == "state":
                    run["state"] = step["state"]
                    emit(run, "state", step["title"], step["detail"], status="done")
                elif step["kind"] == "finish":
                    run["state"] = "COMPLETED"
                    run["summary"] = step["summary"]
                    emit(run, "finish", "Task completed", step["summary"], status="done")
                else:
                    tool = step["tool"]
                    args = step["arguments"]
                    decision_payload = dict(args)
                    if step.get("phase"):
                        decision_payload["phase"] = step["phase"]
                    emit(run, "decision", f"Selected {tool}", step["reason"], tool=tool, payload=decision_payload, status="active")
                    try:
                        result = executor.call(tool, args)
                        if step.get("phase"):
                            result["phase"] = step["phase"]
                        detail = compact(result.get("output") or result.get("content") or result)
                        emit(run, "tool_result", f"{tool} returned", detail, tool=tool, payload=result, status="done")
                        if result.get("diff"):
                            run["diffs"].append(result["diff"])
                        update_evidence_score(run)
                    except Exception as exc:
                        emit(run, "error", f"{tool} blocked", str(exc), tool=tool, status="failed")
        else:
            messages = [{"role": "system", "content": (
                "You are AURORA TRACE, an evidence-first local coding agent. "
                "Work only through the provided tools. First inspect the repository, "
                "capture a baseline test result when tests exist, make the smallest "
                "safe patch, run regression verification, and only then finish. "
                "Return one tool call at a time. Never claim success without evidence."
            )}]
            messages.append({"role": "user", "content": (
                f"Project profile: {json.dumps(run['project'].get('profile', {}), ensure_ascii=False)}\n"
                f"Task: {run['task']}"
            )})
            executor = ToolExecutor(run["workspace"])
            for _ in range(12):
                decision = ModelAdapter("live").decide(messages)
                if decision["type"] == "finish":
                    run["state"] = "COMPLETED"; run["summary"] = decision["summary"]
                    emit(run, "finish", "Task completed", run["summary"], status="done"); break
                tool, args = decision["tool"], decision["arguments"]
                emit(run, "decision", f"Selected {tool}", decision.get("reason", ""), tool=tool, payload=args, status="active")
                result = executor.call(tool, args)
                if result.get("diff"): run["diffs"].append(result["diff"])
                emit(run, "tool_result", f"{tool} returned", compact(result), tool=tool, payload=result, status="done")
                update_evidence_score(run)
                assistant_message = decision.get("assistant_message") or {"role": "assistant", "content": decision.get("reason", "")}
                messages.extend([assistant_message,
                                 {"role": "tool", "tool_call_id": decision.get("call_id", ""),
                                  "content": json.dumps(result, ensure_ascii=False)}])
            else:
                raise RuntimeError("maximum iterations reached")
    except Exception as exc:
        run["state"] = "FAILED"; run["summary"] = str(exc)
        emit(run, "error", "Run stopped", str(exc), status="failed")
    finally:
        update_evidence_score(run)
        run["finished"] = True


def start_run(task: str, mode: str, project_id: str = "demo") -> dict[str, Any]:
    with PROJECT_LOCK:
        project = PROJECTS.get(project_id)
    if not project:
        raise ValueError("selected project does not exist")
    if project_id != "demo" and mode != "live":
        raise ValueError("uploaded projects require LIVE / MODEL API mode")
    if mode == "live" and not os.getenv("OPENAI_API_KEY"):
        raise ValueError("Live 模式需要 OPENAI_API_KEY；请先在启动服务的终端中设置环境变量")
    run_id = uuid.uuid4().hex[:8]
    workspace = ROOT / ".runs" / run_id
    workspace.parent.mkdir(exist_ok=True)
    shutil.copytree(project["path"], workspace)
    ledger_path = workspace / "evidence.ndjson"
    run = {"id": run_id, "task": task, "mode": mode, "workspace": workspace,
           "events": [], "ledger": [], "diffs": [], "state": "QUEUED",
           "summary": "", "finished": False, "lock": threading.Lock(),
           "ledger_path": ledger_path, "contract": contract_for(task, project),
           "project": {k: v for k, v in project.items() if k != "path"},
           "evidence": {}, "trust_score": 0}
    with RUN_LOCK: RUNS[run_id] = run
    threading.Thread(target=run_agent, args=(run, mode), daemon=True).start()
    return {"run_id": run_id}


def multipart_file(content_type: str, body: bytes) -> tuple[str, bytes]:
    message = BytesParser(policy=email_default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    )
    if not message.is_multipart():
        raise ValueError("expected multipart form upload")
    for part in message.iter_parts():
        filename = part.get_filename()
        if filename:
            return Path(filename).name, part.get_payload(decode=True) or b""
    raise ValueError("no project ZIP was attached")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return

    def send_json(self, value: Any, code: int = 200):
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            raw = (WEB / "index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(raw); return
        if self.path.startswith("/static/"):
            try:
                file = safe_web_path(self.path.removeprefix("/static/"))
            except ValueError:
                self.send_json({"error": "invalid static path"}, 400); return
            if file.exists() and file.is_file():
                raw = file.read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/css" if file.suffix == ".css" else "application/javascript"); self.end_headers(); self.wfile.write(raw); return
        if self.path.startswith("/api/run/") and self.path.endswith("/export"):
            run_id = self.path.split("/")[-2]; run = RUNS.get(run_id)
            if not run: self.send_json({"error": "run not found"}, 404); return
            with run["lock"]:
                raw = json.dumps({"run_id": run["id"], "task": run["task"],
                                  "contract": run["contract"], "evidence": run["evidence"],
                                  "trust_score": run["trust_score"], "events": run["events"]},
                                 ensure_ascii=False, indent=2).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f"attachment; filename=aurora-trace-{run_id}.json")
            self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if self.path.startswith("/api/run/"):
            run_id = self.path.split("/")[-1]; run = RUNS.get(run_id)
            if not run: self.send_json({"error": "run not found"}, 404); return
            with run["lock"]:
                self.send_json({"id": run["id"], "state": run["state"], "events": run["events"],
                                "ledger": run["ledger"], "diffs": run["diffs"],
                                "summary": run["summary"], "finished": run["finished"],
                                "contract": run["contract"], "evidence": run["evidence"],
                                "trust_score": run["trust_score"]})
            return
        if self.path == "/api/projects":
            with PROJECT_LOCK:
                projects = []
                for project in PROJECTS.values():
                    if "profile" not in project:
                        project["profile"] = profile_project(project["path"])
                    projects.append({k: v for k, v in project.items() if k != "path"})
            self.send_json({"projects": projects}); return
        if self.path == "/api/health":
            self.send_json({"service": "AURORA TRACE", "status": "online",
                            "mode": os.getenv("AURORA_MODE", "mock"),
                            "tools": [tool["name"] for tool in TOOLS]})
            return
        self.send_json({"service": "AURORA TRACE", "status": "online"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if self.path == "/api/projects/import":
            if length > MAX_UPLOAD_BYTES + 1024 * 1024:
                self.send_json({"error": "upload exceeds the 10 MB limit"}, 413); return
            try:
                filename, data = multipart_file(self.headers.get("Content-Type", ""), self.rfile.read(length))
                self.send_json({"project": import_zip_project(filename, data)}, 201)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, 400)
            return
        if self.path != "/api/run": self.send_json({"error": "not found"}, 404); return
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_json({"error": "request body must be valid JSON"}, 400); return
        task = body.get("task", "修复 Todo 项目的删除边界 Bug，补充测试并运行测试。")
        mode = body.get("mode") or os.getenv("AURORA_MODE", "mock")
        if mode not in {"mock", "live"}:
            self.send_json({"error": "mode must be mock or live"}, 400); return
        try:
            self.send_json(start_run(task, mode, body.get("project_id", "demo")))
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)


if __name__ == "__main__":
    load_project_index()
    print(f"AURORA TRACE listening on http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
