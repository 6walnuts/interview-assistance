"""Provider resolution logic for the multi-provider LLM config (no network)."""
from app.config import Settings


def test_default_provider_is_openai_with_legacy_alias():
    s = Settings(openai_api_key="sk-legacy", mock_ai=False)
    assert s.llm_provider == "openai"
    assert s.resolved_api_key == "sk-legacy"
    assert s.resolved_model == "gpt-4o-mini"
    assert s.resolved_base_url is None
    assert s.ai_enabled


def test_deepseek_defaults():
    s = Settings(llm_provider="deepseek", llm_api_key="sk-ds", mock_ai=False)
    assert s.resolved_base_url == "https://api.deepseek.com"
    assert s.resolved_model == "deepseek-chat"
    assert s.ai_enabled


def test_kimi_defaults_and_model_override():
    s = Settings(llm_provider="kimi", llm_api_key="sk-kimi", llm_model="moonshot-v1-8k", mock_ai=False)
    assert s.resolved_base_url == "https://api.moonshot.cn/v1"
    assert s.resolved_model == "moonshot-v1-8k"


def test_anthropic_defaults():
    s = Settings(llm_provider="anthropic", llm_api_key="sk-ant", mock_ai=False)
    assert s.resolved_model == "claude-opus-4-8"
    assert s.resolved_base_url is None
    assert s.ai_enabled


def test_no_key_means_mock_mode():
    s = Settings(llm_provider="anthropic", mock_ai=False)
    assert not s.ai_enabled


def test_legacy_openai_key_does_not_leak_to_other_providers():
    s = Settings(llm_provider="deepseek", openai_api_key="sk-legacy", mock_ai=False)
    assert s.resolved_api_key == ""
    assert not s.ai_enabled


def test_language_instruction():
    from app.agents.prompts import language_instruction

    assert language_instruction("en") == ""
    assert "简体中文" in language_instruction("zh")
    assert "español" in language_instruction("es")
    assert language_instruction("fr") == ""  # unknown locales fall back to English


def test_profile_locale_roundtrip(client, auth_headers):
    resp = client.put("/api/profile", headers=auth_headers, json={"locale": "zh"})
    assert resp.status_code == 200
    assert resp.json()["profile"]["locale"] == "zh"
    assert client.put("/api/profile", headers=auth_headers,
                      json={"locale": "jp"}).status_code == 422
