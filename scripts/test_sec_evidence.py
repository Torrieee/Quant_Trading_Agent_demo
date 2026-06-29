#!/usr/bin/env python3
"""
SEC Evidence 手动测试脚本。

用法（项目根目录）:
  python scripts/test_sec_evidence.py
  python scripts/test_sec_evidence.py AAPL
  python scripts/test_sec_evidence.py MSFT --full

需可访问 https://www.sec.gov
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    parser = argparse.ArgumentParser(description="测试 SEC EDGAR Evidence ingest")
    parser.add_argument("symbol", nargs="?", default="AAPL", help="美股 ticker，默认 AAPL")
    parser.add_argument(
        "--full",
        action="store_true",
        help="跑完整 document_retrieval + search_evidence（不调用 DeepSeek）",
    )
    args = parser.parse_args()

    _load_dotenv()
    os.environ.setdefault("EVIDENCE_FETCH_SEC", "1")

    from quant_agent.evidence.config import is_sec_fetch_enabled, sec_user_agent
    from quant_agent.evidence.plugins.sec_edgar import fetch_sec_filing_excerpts
    from quant_agent.evidence import EvidenceRetriever

    symbol = args.symbol.upper()
    print("=" * 60)
    print("SEC Evidence 测试")
    print("=" * 60)
    print(f"symbol              : {symbol}")
    print(f"EVIDENCE_FETCH_SEC  : {os.environ.get('EVIDENCE_FETCH_SEC', '1')}")
    print(f"enabled             : {is_sec_fetch_enabled()}")
    print(f"User-Agent          : {sec_user_agent()}")
    print()

    print("[1/3] 直连 SEC EDGAR ...")
    try:
        sec_chunks = fetch_sec_filing_excerpts(symbol)
    except Exception as exc:
        print(f"  失败: {exc}")
        print("\n排查: 1) 网络能否打开 sec.gov  2) 设置 EVIDENCE_SEC_USER_AGENT 含真实邮箱")
        return 1

    if not sec_chunks:
        print("  未获取到 SEC 片段（ticker 无效或 filing 为空）")
        return 1

    c = sec_chunks[0]
    print(f"  OK: {c.doc_type} | filed={c.published_at}")
    print(f"  URL: {c.source_url}")
    print(f"  文本预览 ({len(c.text)} chars):\n  {c.text[:400]}...\n")

    print("[2/3] EvidenceRetriever 索引 + snapshot ...")
    retriever = EvidenceRetriever()
    n = retriever.ensure_index(symbol, stock_info={"symbol": symbol})
    snapshot = retriever.get_snapshot(symbol, f"Analyze {symbol} risk and outlook")
    sec_in = [x for x in snapshot if x.source == "sec_edgar" or x.doc_type in ("10-K", "10-Q")]
    print(f"  总 chunk: {n}, snapshot: {len(snapshot)}, 含 SEC: {len(sec_in)}")
    fields = retriever.snapshot_to_state(snapshot)
    print(f"  risk_flags: {fields.get('risk_flags')}")
    print(f"  event_severity: {fields.get('document_flags', {}).get('event_severity')}")
    print()

    if args.full:
        print("[3/3] search_evidence 工具 ...")
        from quant_agent.llm_agent import TradingFunctionCaller

        caller = TradingFunctionCaller(evidence_retriever=retriever)
        out = caller.call_function(
            "search_evidence",
            {"symbol": symbol, "query": "risk factors competition", "top_k": 3},
        )
        print(f"  命中: {out.get('count')} 条")
        for i, doc in enumerate(out.get("retrieved_documents") or [], 1):
            print(f"  [{i}] {doc.get('doc_type')} | {doc.get('source')} | score={doc.get('score')}")
    else:
        print("[3/3] 跳过 search_evidence（加 --full 可测）")

    print("\n完成。若要跑完整 QuantEngine（需 DEEPSEEK_API_KEY）:")
    print(f'  python -c "from quant_agent import QuantEngine; r=QuantEngine().analyze(\'{symbol}\'); print(r.final_state.get(\'evidence_snapshot\', [])[:1])"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
