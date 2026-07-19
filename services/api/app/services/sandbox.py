"""Python code execution sandbox.

Default mode "docker" enforces: no network, CPU/memory caps, pids-limit
(fork-bomb protection), read-only rootfs with a small tmpfs, nobody user,
no environment variables, and a host-side kill timeout (infinite-loop
protection). Code is passed on stdin — nothing from the host is mounted.

Mode "subprocess" exists ONLY for local development without Docker and
provides no isolation.
"""
import json
import subprocess
import time
import uuid
from dataclasses import dataclass, field

from ..config import get_settings

@dataclass
class ExecutionResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    duration_ms: int = 0
    test_results: list[dict] = field(default_factory=list)


def _build_program(code: str, test_cases: list[dict]) -> str:
    """Wrap user code with a tiny test harness.

    Each test case: {"name", "call" (python expression), "expected" (json)}.
    Harness prints one JSON line per test prefixed with __TEST__ so results
    survive alongside the user's own prints.
    """
    return (
        "import json as _json\n"
        + code
        + "\n\n_tests = _json.loads('''" + json.dumps(test_cases) + "''')\n"
        + "for _t in _tests:\n"
        + "    try:\n"
        + "        _actual = eval(_t['call'])\n"
        + "        _passed = _actual == _t['expected']\n"
        + "        _detail = '' if _passed else f\"expected {_t['expected']!r}, got {_actual!r}\"\n"
        + "    except Exception as _e:\n"
        + "        _passed, _detail = False, f'{type(_e).__name__}: {_e}'\n"
        + "    print('__TEST__' + _json.dumps({'name': _t['name'], 'passed': _passed, 'detail': _detail}))\n"
    )


def _parse_output(raw_stdout: str) -> tuple[str, list[dict]]:
    stdout_lines, tests = [], []
    for line in raw_stdout.splitlines():
        if line.startswith("__TEST__"):
            try:
                tests.append(json.loads(line[len("__TEST__"):]))
            except json.JSONDecodeError:
                pass
        else:
            stdout_lines.append(line)
    return "\n".join(stdout_lines), tests


def run_python(code: str, test_cases: list[dict] | None = None) -> ExecutionResult:
    settings = get_settings()
    program = _build_program(code, test_cases or []) if test_cases else code

    if settings.sandbox_mode == "docker":
        cmd = [
            "docker", "run", "--rm", "-i",
            "--name", f"ai-coach-run-{uuid.uuid4().hex[:12]}",
            "--network", "none",
            "--cpus", settings.sandbox_cpus,
            "--memory", settings.sandbox_memory,
            "--pids-limit", "64",
            "--read-only", "--tmpfs", "/tmp:size=16m",
            "--user", "65534:65534",
            "--env", "PYTHONUNBUFFERED=1",
            settings.sandbox_image,
            "python3", "-I", "-c", "import sys; exec(sys.stdin.read())",
        ]
    else:  # subprocess: dev-only, NOT isolated
        cmd = ["python3", "-I", "-c", "import sys; exec(sys.stdin.read())"]

    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, input=program, capture_output=True, text=True,
            timeout=settings.sandbox_timeout_seconds,
        )
        raw_stdout, exit_code, timed_out = proc.stdout, proc.returncode, False
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        raw_stdout = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = "Execution timed out (possible infinite loop)."
        exit_code, timed_out = -1, True
    except FileNotFoundError:
        return ExecutionResult(stderr="Sandbox runtime not available on this host.", exit_code=-1)

    duration_ms = int((time.monotonic() - start) * 1000)
    stdout, tests = _parse_output(raw_stdout)
    return ExecutionResult(
        stdout=stdout[:20_000], stderr=stderr[:20_000], exit_code=exit_code,
        timed_out=timed_out, duration_ms=duration_ms, test_results=tests,
    )
