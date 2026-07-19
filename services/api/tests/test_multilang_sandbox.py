"""Multi-language sandbox execution (subprocess mode; skips if a toolchain is absent)."""
import shutil

import pytest

from app.services.sandbox import LANGUAGES, run_code

TESTS = [{"name": "example", "call": "two_sum([2,7,11,15], 9)", "expected": [0, 1]},
         {"name": "duplicates", "call": "two_sum([3,3], 6)", "expected": [0, 1]}]


def _has(lang: str) -> bool:
    return all(shutil.which(b) for b in LANGUAGES[lang].required_binaries)


def test_javascript_harness_passes(client):
    code = """function two_sum(nums, target) {
  const seen = new Map();
  for (let i = 0; i < nums.length; i++) {
    if (seen.has(target - nums[i])) return [seen.get(target - nums[i]), i];
    seen.set(nums[i], i);
  }
  return [];
}"""
    result = run_code(code, "javascript", TESTS)
    assert result.exit_code == 0, result.stderr
    assert len(result.test_results) == 2 and all(t["passed"] for t in result.test_results)


def test_javascript_harness_reports_failure(client):
    result = run_code("function two_sum() { return null; }", "javascript", TESTS)
    assert result.exit_code == 0
    assert result.test_results and not any(t["passed"] for t in result.test_results)


@pytest.mark.skipif(not _has("go"), reason="go toolchain not installed")
def test_go_program_mode(client):
    code = """package main

import "fmt"

func twoSum(nums []int, target int) []int {
    seen := map[int]int{}
    for i, n := range nums {
        if j, ok := seen[target-n]; ok {
            return []int{j, i}
        }
        seen[n] = i
    }
    return nil
}

func main() {
    fmt.Println(twoSum([]int{2, 7, 11, 15}, 9))
}"""
    result = run_code(code, "go")
    assert result.exit_code == 0, result.stderr
    assert "[0 1]" in result.stdout
    assert result.test_results == []  # no harness for compiled languages


@pytest.mark.skipif(not _has("java"), reason="jdk not installed")
def test_java_program_mode(client):
    code = """public class Main {
    public static void main(String[] args) {
        System.out.println(1 + 2);
    }
}"""
    result = run_code(code, "java")
    assert result.exit_code == 0, result.stderr
    assert result.stdout.strip() == "3"


@pytest.mark.skipif(not _has("cpp"), reason="g++ not installed")
def test_cpp_compile_error_surfaces(client):
    result = run_code("int main() { return 0 }", "cpp")  # missing semicolon
    assert result.exit_code != 0
    assert "error" in result.stderr.lower()


def test_run_code_api_accepts_javascript(client):
    # Fresh user: question selection prefers unseen questions, so a shared
    # user would drift to other bank questions as earlier tests consume them.
    reg = client.post("/api/auth/register", json={
        "email": "js-sandbox@example.com", "password": "secret123", "name": "JS Runner",
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    created = client.post("/api/interviews", headers=headers, json={
        "interview_type": "coding", "role": "Backend Engineer", "level": "mid",
        "difficulty": "easy", "language": "javascript", "focus_areas": ["hash-map"],
    }).json()
    auth_headers = headers
    session_id = created["session"]["id"]
    resp = client.post(f"/api/interviews/{session_id}/run-code", headers=auth_headers, json={
        "code": "function two_sum(n, t) { for (let i=0;i<n.length;i++) for (let j=i+1;j<n.length;j++) if (n[i]+n[j]===t) return [i,j]; return []; }",
        "language": "javascript", "label": "run",
    })
    assert resp.status_code == 200
    execution = resp.json()["execution"]
    assert execution["exit_code"] == 0, execution["stderr"]
    assert execution["test_results"] and all(t["passed"] for t in execution["test_results"])


def test_run_code_api_rejects_unknown_language(client, auth_headers):
    created = client.post("/api/interviews", headers=auth_headers, json={
        "interview_type": "coding", "role": "Backend Engineer", "level": "mid",
        "difficulty": "easy", "focus_areas": [],
    }).json()
    resp = client.post(f"/api/interviews/{created['session']['id']}/run-code",
                       headers=auth_headers,
                       json={"code": "x", "language": "ruby", "label": "run"})
    assert resp.status_code == 422
