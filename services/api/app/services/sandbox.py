"""Multi-language code execution sandbox.

Supported: python, javascript (Node), go, java, cpp.
- python/javascript additionally run the question's test cases through an
  in-process harness (results parsed from __TEST__ lines).
- go/java/cpp run as complete programs (CoderPad style): the candidate writes
  their own main and test calls; stdout/stderr are returned as-is.

Default mode "docker" enforces per-language images with: no network, CPU and
memory caps, pids-limit (fork-bomb protection), read-only rootfs with an
exec-enabled tmpfs (compilers need it), nobody user, no inherited environment,
and a host-side kill timeout. Code is passed on stdin — nothing is mounted.

Mode "subprocess" exists ONLY for local development without Docker and
provides no isolation; it requires the language toolchain on the host.
"""
import json
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field

from ..config import get_settings


@dataclass(frozen=True)
class LanguageSpec:
    image: str
    filename: str
    # Shell command run inside the sandbox; the program text arrives on stdin.
    run_cmd: str
    memory: str
    timeout_extra: int          # compile headroom added to the base timeout
    env: tuple[tuple[str, str], ...]
    harness: bool               # automated test-case harness available
    required_binaries: tuple[str, ...]  # for subprocess mode


LANGUAGES: dict[str, LanguageSpec] = {
    "python": LanguageSpec(
        image="ai-coach-sandbox-python:latest", filename="main.py",
        run_cmd="cat > /tmp/main.py && python3 -I /tmp/main.py",
        memory="256m", timeout_extra=0, env=(("PYTHONUNBUFFERED", "1"),),
        harness=True, required_binaries=("python3",)),
    "javascript": LanguageSpec(
        image="ai-coach-sandbox-javascript:latest", filename="main.js",
        run_cmd="cat > /tmp/main.js && node /tmp/main.js",
        memory="256m", timeout_extra=0, env=(),
        harness=True, required_binaries=("node",)),
    "go": LanguageSpec(
        image="ai-coach-sandbox-go:latest", filename="main.go",
        run_cmd="cat > /tmp/main.go && cd /tmp && go run main.go",
        memory="768m", timeout_extra=30,
        env=(("GOCACHE", "/tmp/gocache"), ("GOPATH", "/tmp/go"),
             ("HOME", "/tmp"), ("CGO_ENABLED", "0")),
        harness=False, required_binaries=("go",)),
    "java": LanguageSpec(
        image="ai-coach-sandbox-java:latest", filename="Main.java",
        run_cmd="cat > /tmp/Main.java && cd /tmp && javac Main.java && java Main",
        memory="768m", timeout_extra=20, env=(("HOME", "/tmp"),),
        harness=False, required_binaries=("javac", "java")),
    "cpp": LanguageSpec(
        image="ai-coach-sandbox-cpp:latest", filename="main.cpp",
        run_cmd="cat > /tmp/main.cpp && g++ -O2 -std=c++17 -o /tmp/a.out /tmp/main.cpp && /tmp/a.out",
        memory="512m", timeout_extra=20, env=(("HOME", "/tmp"),),
        harness=False, required_binaries=("g++",)),
}


@dataclass
class ExecutionResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    duration_ms: int = 0
    test_results: list[dict] = field(default_factory=list)


def _python_harness(code: str, test_cases: list[dict]) -> str:
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


def _javascript_harness(code: str, test_cases: list[dict]) -> str:
    # The stored `call` expression ("two_sum([2,7], 9)") is literal-compatible
    # JS as long as the candidate uses the same function name.
    return (
        code
        + "\n\nconst _tests = " + json.dumps(test_cases) + ";\n"
        + "const _eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);\n"
        + "for (const _t of _tests) {\n"
        + "  let _line;\n"
        + "  try {\n"
        + "    const _actual = eval(_t.call);\n"
        + "    const _passed = _eq(_actual, _t.expected);\n"
        + "    _line = { name: _t.name, passed: _passed, detail: _passed ? '' :\n"
        + "      `expected ${JSON.stringify(_t.expected)}, got ${JSON.stringify(_actual)}` };\n"
        + "  } catch (_e) { _line = { name: _t.name, passed: false, detail: String(_e) }; }\n"
        + "  console.log('__TEST__' + JSON.stringify(_line));\n"
        + "}\n"
    )


def _build_program(language: str, code: str, test_cases: list[dict]) -> str:
    spec = LANGUAGES[language]
    if not spec.harness or not test_cases:
        return code
    if language == "python":
        return _python_harness(code, test_cases)
    return _javascript_harness(code, test_cases)


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


def _docker_cmd(spec: LanguageSpec, settings) -> list[str]:
    cmd = [
        "docker", "run", "--rm", "-i",
        "--name", f"ai-coach-run-{uuid.uuid4().hex[:12]}",
        "--network", "none",
        "--cpus", settings.sandbox_cpus,
        "--memory", spec.memory,
        "--pids-limit", "128",
        "--read-only", "--tmpfs", "/tmp:size=512m,exec",
        "--user", "65534:65534",
    ]
    for key, value in spec.env:
        cmd += ["--env", f"{key}={value}"]
    cmd += [spec.image, "sh", "-c", spec.run_cmd]
    return cmd


def run_code(code: str, language: str = "python",
             test_cases: list[dict] | None = None) -> ExecutionResult:
    settings = get_settings()
    spec = LANGUAGES.get(language)
    if spec is None:
        return ExecutionResult(stderr=f"Unsupported language: {language}", exit_code=-1)

    program = _build_program(language, code, test_cases or [])
    timeout = settings.sandbox_timeout_seconds + spec.timeout_extra

    workdir: tempfile.TemporaryDirectory | None = None
    if settings.sandbox_mode == "docker":
        cmd = _docker_cmd(spec, settings)
        run_kwargs: dict = {"input": program}
    else:  # subprocess: dev-only, NOT isolated
        missing = [b for b in spec.required_binaries if shutil.which(b) is None]
        if missing:
            return ExecutionResult(
                stderr=f"Runtime not available on this host: {', '.join(missing)}. "
                       f"Install it or use SANDBOX_MODE=docker.", exit_code=-1)
        workdir = tempfile.TemporaryDirectory(prefix="ai-coach-run-")
        local_cmd = spec.run_cmd.replace("/tmp/", f"{workdir.name}/").replace("cd /tmp", f"cd {workdir.name}")
        cmd = ["sh", "-c", local_cmd]
        run_kwargs = {"input": program}

    start = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **run_kwargs)
        raw_stdout, stderr, exit_code, timed_out = proc.stdout, proc.stderr, proc.returncode, False
    except subprocess.TimeoutExpired as exc:
        raw_stdout = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = "Execution timed out (possible infinite loop)."
        exit_code, timed_out = -1, True
    except FileNotFoundError:
        return ExecutionResult(stderr="Sandbox runtime not available on this host.", exit_code=-1)
    finally:
        if workdir is not None:
            workdir.cleanup()

    duration_ms = int((time.monotonic() - start) * 1000)
    stdout, tests = _parse_output(raw_stdout)
    return ExecutionResult(
        stdout=stdout[:20_000], stderr=stderr[:20_000], exit_code=exit_code,
        timed_out=timed_out, duration_ms=duration_ms, test_results=tests,
    )


def run_python(code: str, test_cases: list[dict] | None = None) -> ExecutionResult:
    """Backward-compatible wrapper."""
    return run_code(code, "python", test_cases)
