"""Teste de carga da API: degraus de concorrência sobre /search e /ask.

Mede latência (p50/p95/p99), vazão e taxa de erro com as perguntas do conjunto de
DESENVOLVIMENTO (nunca o de teste). Usa só httpx, que já é dependência do projeto.

  python scripts/load_test.py --endpoint search --concurrency 1,4,16,32 --requests 100
  python scripts/load_test.py --endpoint ask --concurrency 1,2,4 --requests 8 --out carga.json

/search mede recuperação (embedding + Qdrant + BM25 + fusão), sem o LLM. /ask mede o fluxo
completo; com um LLM em CPU a geração domina e, como o Ollama atende uma geração por vez,
a latência cresce com a concorrência (enfileiramento), e não a vazão.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEV_DATASET = ROOT / "eval" / "datasets" / "perguntas_dev.json"


def percentile(values: list[float], p: float) -> float:
    """Percentil pelo método do posto mais próximo (sem interpolar)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


def summarize(samples: list[dict], wall_s: float) -> dict:
    """Resume as amostras de um degrau; só as requisições com sucesso entram na latência."""
    ok = [s for s in samples if s["ok"]]
    latencies = [s["ms"] for s in ok]
    refused = sum(bool(s.get("refused")) for s in ok)
    return {
        "requests": len(samples),
        "errors": len(samples) - len(ok),
        "error_rate": round((len(samples) - len(ok)) / len(samples), 4) if samples else 0.0,
        "refused": refused,
        "throughput_rps": round(len(ok) / wall_s, 3) if wall_s > 0 else 0.0,
        "p50_ms": round(percentile(latencies, 50), 1),
        "p95_ms": round(percentile(latencies, 95), 1),
        "p99_ms": round(percentile(latencies, 99), 1),
        "max_ms": round(max(latencies, default=0.0), 1),
    }


def load_questions(path: Path = DEV_DATASET) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [q["question"] for q in data["questions"]]


async def _one(client: httpx.AsyncClient, endpoint: str, question: str, top_k: int) -> dict:
    start = time.perf_counter()
    try:
        response = await client.post(endpoint, json={"question": question, "top_k": top_k})
        ms = (time.perf_counter() - start) * 1000
        ok = response.status_code == 200
        refused = ok and bool(response.json().get("refused"))
        return {"ok": ok, "ms": ms, "status": response.status_code, "refused": refused}
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "ms": (time.perf_counter() - start) * 1000,
            "status": type(exc).__name__,
        }


async def run_step(
    client: httpx.AsyncClient, endpoint: str, questions: list[str], concurrency: int, total: int
) -> dict:
    """Dispara `total` requisições com no máximo `concurrency` em voo ao mesmo tempo."""
    gate = asyncio.Semaphore(concurrency)

    async def worker(index: int) -> dict:
        async with gate:
            return await _one(client, endpoint, questions[index % len(questions)], top_k=5)

    start = time.perf_counter()
    samples = await asyncio.gather(*(worker(i) for i in range(total)))
    result = summarize(list(samples), time.perf_counter() - start)
    result["concurrency"] = concurrency
    statuses = sorted({str(s["status"]) for s in samples if not s["ok"]})
    if statuses:
        result["error_statuses"] = statuses
    return result


async def run(url: str, endpoint: str, steps: list[int], total: int, timeout: float) -> list[dict]:
    questions = load_questions()
    results = []
    async with httpx.AsyncClient(base_url=url, timeout=timeout) as client:
        health = await client.get("/health")
        health.raise_for_status()
        for concurrency in steps:
            result = await run_step(client, endpoint, questions, concurrency, total)
            results.append(result)
            print(_row(result), flush=True)
            if result["error_rate"] > 0.5:
                print("Mais de 50% de erros: interrompendo os degraus seguintes.")
                break
    return results


def _row(r: dict) -> str:
    return (
        f"c={r['concurrency']:<3} n={r['requests']:<4} erros={r['errors']:<3} "
        f"recusas={r['refused']:<3} rps={r['throughput_rps']:<7} p50={r['p50_ms']:>9.1f}ms "
        f"p95={r['p95_ms']:>9.1f}ms p99={r['p99_ms']:>9.1f}ms max={r['max_ms']:>9.1f}ms"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--endpoint", choices=["search", "ask"], default="search")
    parser.add_argument("--concurrency", default="1,4,16", help="degraus separados por vírgula")
    parser.add_argument("--requests", type=int, default=50, help="requisições por degrau")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, help="grava o resultado em JSON")
    args = parser.parse_args(argv)
    steps = [int(x) for x in args.concurrency.split(",") if x.strip()]
    if not steps or min(steps) < 1 or args.requests < 1:
        parser.error("--concurrency e --requests precisam ser inteiros positivos")
    try:
        results = asyncio.run(
            run(args.url, f"/{args.endpoint}", steps, args.requests, args.timeout)
        )
    except httpx.HTTPError as exc:
        print(f"API indisponível em {args.url}: {exc}", file=sys.stderr)
        return 1
    if args.out:
        payload = {"url": args.url, "endpoint": args.endpoint, "steps": results}
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
