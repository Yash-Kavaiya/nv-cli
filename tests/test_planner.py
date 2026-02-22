"""Tests for nvcli.agent.planner."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from nvcli.agent.planner import (
    Plan, PlanStep, _parse_plan_json, _collect_repo_context, _build_tree, generate_plan
)

class TestParsePlanJson:
    def test_parse_valid_json(self):
        raw = '''{"summary": "Add logging", "steps": [
            {"n": 1, "description": "Read file", "tool": "read_file", "args": {"path": "app.py"}}
        ]}'''
        plan = _parse_plan_json(raw)
        assert plan.summary == "Add logging"
        assert len(plan.steps) == 1
        assert plan.steps[0].tool == "read_file"

    def test_parse_json_wrapped_in_markdown(self):
        raw = '```json\n{"summary": "Test", "steps": []}\n```'
        plan = _parse_plan_json(raw)
        assert plan.summary == "Test"

    def test_parse_json_wrapped_in_backticks_no_lang(self):
        raw = '```\n{"summary": "No lang", "steps": []}\n```'
        plan = _parse_plan_json(raw)
        assert plan.summary == "No lang"

    def test_parse_no_json_raises_value_error(self):
        with pytest.raises(ValueError, match="No JSON object found"):
            _parse_plan_json("Here is my plan: step 1, step 2")

    def test_parse_multiple_steps(self):
        raw = '''{
            "summary": "Multi step",
            "steps": [
                {"n": 1, "description": "Read", "tool": "read_file", "args": {"path": "a.py"}},
                {"n": 2, "description": "Write", "tool": "write_file", "args": {"path": "a.py", "content_hint": "add fn"}},
                {"n": 3, "description": "Test", "tool": "run_cmd", "args": {"command": "pytest"}}
            ]
        }'''
        plan = _parse_plan_json(raw)
        assert len(plan.steps) == 3
        assert plan.steps[2].tool == "run_cmd"
        assert plan.steps[2].args["command"] == "pytest"

    def test_parse_missing_summary_uses_default(self):
        raw = '{"steps": []}'
        plan = _parse_plan_json(raw)
        assert plan.summary == "No summary"


class TestCollectRepoContext:
    def test_collect_returns_string(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')")
        context = _collect_repo_context(str(tmp_path))
        assert isinstance(context, str)
        assert "main.py" in context

    def test_collect_nonexistent_path_returns_partial(self):
        # Should not raise, just return what it can
        context = _collect_repo_context("/nonexistent/path/xyz")
        assert isinstance(context, str)


class TestGeneratePlan:
    @pytest.mark.asyncio
    async def test_generate_plan_calls_api_and_returns_plan(self, tmp_path, monkeypatch):
        """Test that generate_plan calls the API and parses the response."""
        mock_response = '{"summary": "Add logging to main.py", "steps": [{"n": 1, "description": "Read main.py", "tool": "read_file", "args": {"path": "main.py"}}]}'
        
        async def fake_stream(messages, model=None, temperature=None):
            for char in mock_response:
                yield char
        
        mock_client = MagicMock()
        mock_client.stream_chat = fake_stream
        
        monkeypatch.setattr("nvcli.agent.planner.get_client", lambda cfg: mock_client)
        
        plan = await generate_plan("Add logging to main.py", context_path=str(tmp_path))
        assert plan.summary == "Add logging to main.py"
        assert len(plan.steps) == 1
