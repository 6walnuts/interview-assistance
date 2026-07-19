"""Scratchpad code execution: run code in the sandbox outside an interview.

Used by the tutor lesson page. Same sandbox and limits as interview runs,
but with no test cases — the program's own output is the result.
"""
from fastapi import APIRouter, Depends

from ..models import User
from ..schemas import ExecutionOut, ScratchRunRequest, TestResultOut
from ..security import get_current_user
from ..services.sandbox import run_code as sandbox_run_code

router = APIRouter(prefix="/api/code", tags=["code"])


@router.post("/run", response_model=ExecutionOut)
def run_scratch(body: ScratchRunRequest, user: User = Depends(get_current_user)) -> ExecutionOut:
    result = sandbox_run_code(body.code, body.language, [])
    return ExecutionOut(
        stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code,
        timed_out=result.timed_out, duration_ms=result.duration_ms,
        test_results=[TestResultOut(**t) for t in result.test_results],
    )
