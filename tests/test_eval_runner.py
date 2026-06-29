"""Agent 评测 runner 测试。"""



from __future__ import annotations



import os

from pathlib import Path



import pytest



from quant_agent.agents.llm import has_deepseek_api_key

from quant_agent.eval import AgentEvalRunner, load_evalset

from quant_agent.eval.benchmark import check_benchmark





def test_load_regression_evalset():

    path = Path(__file__).resolve().parents[1] / "evalsets" / "regression_v1.yaml"

    spec = load_evalset(path)

    assert spec["evalset_id"] == "regression_v1"

    assert len(spec["cases"]) >= 10





def test_load_capability_evalset():

    path = Path(__file__).resolve().parents[1] / "evalsets" / "capability_v1.yaml"

    spec = load_evalset(path)

    assert spec["evalset_id"] == "capability_v1"

    assert spec["model"] == "live"

    assert len(spec["cases"]) >= 6

    assert spec["benchmark"]["min_pass_rate"] < 1.0





def test_regression_eval_offline_passes():

    path = Path(__file__).resolve().parents[1] / "evalsets" / "regression_v1.yaml"

    report = AgentEvalRunner(evalset_path=path).run_evalset()

    sc = report["scorecard"]

    assert sc["case_count"] >= 10

    assert sc["summary"]["pass_rate"] >= 0.9, sc["cases"]

    assert report["benchmark"]["passed"] is True





def test_benchmark_gate_detects_low_pass_rate():

    scorecard = {

        "summary": {"pass_rate": 0.5},

    }

    result = check_benchmark(scorecard, {"min_pass_rate": 0.67})

    assert result["passed"] is False





@pytest.mark.integration

@pytest.mark.skipif(not has_deepseek_api_key(), reason="DEEPSEEK_API_KEY not set")

def test_capability_live_eval_smoke():

    """本地有 API Key 时跑 1 条 live case 冒烟（全量请用 scripts/run_eval.py --live）。"""

    path = Path(__file__).resolve().parents[1] / "evalsets" / "capability_v1.yaml"

    spec = load_evalset(path)

    one_case = {**spec, "cases": spec["cases"][:1]}

    import yaml

    import tempfile



    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:

        yaml.safe_dump(one_case, f, allow_unicode=True)

        tmp = Path(f.name)

    try:

        report = AgentEvalRunner(evalset_path=tmp).run_evalset(enable_judge=False)

        assert report["scorecard"]["case_count"] == 1

        assert report["results"][0].get("report") or report["results"][0].get("failures")

    finally:

        tmp.unlink(missing_ok=True)

