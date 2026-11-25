"""Scripts de instalação: verificador de dependências e codificação dos .ps1."""

import re
from importlib import metadata
from pathlib import Path

import pytest

from scripts import verificar_dependencias as vd

ROOT = Path(__file__).resolve().parents[1]
PS_SCRIPTS = sorted((ROOT / "scripts").glob("*.ps1"))


def test_pins_read_from_real_pyproject():
    pins = vd.pinned_requirements()
    assert pins["fastapi"] == "0.115.5"
    assert pins["uvicorn"] == "0.32.1"  # o extra [standard] não entra no nome
    assert pins["pydantic-settings"] == "2.6.1"
    assert pins["streamlit"] == "1.40.1"  # extra ui
    assert pins["pytest"] == "8.3.3"  # extra dev


def test_pins_ignore_unpinned_and_unknown_extras(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'dependencies = ["Foo_Bar==1.0", "livre>=2", "marcado==3.1 ; python_version >= \'3.11\'"]\n'
        "[project.optional-dependencies]\n"
        'dev = ["ferramenta==0.5"]\n',
        encoding="utf-8",
    )
    assert vd.pinned_requirements(pyproject, extras=("dev", "inexistente")) == {
        "foo-bar": "1.0",
        "marcado": "3.1",
        "ferramenta": "0.5",
    }


def test_find_problems_reports_missing_and_wrong_versions():
    installed = {"certo": "1.0", "velho": "0.9"}

    def version_of(name):
        if name not in installed:
            raise metadata.PackageNotFoundError(name)
        return installed[name]

    problems = vd.find_problems({"certo": "1.0", "velho": "1.0", "ausente": "2.0"}, version_of)
    assert problems == [
        "ausente: não instalado (esperado 2.0)",
        "velho: versão 0.9 instalada, esperado 1.0",
    ]


def test_missing_project_packages_uses_find_spec():
    assert vd.missing_project_packages(lambda name: None if name == "ui" else object()) == ["ui"]


@pytest.mark.parametrize("problems, code", [([], 0), (["fastapi: não instalado"], 1)])
def test_main_exit_code(monkeypatch, capsys, problems, code):
    monkeypatch.setattr(vd, "find_problems", lambda pins: list(problems))
    monkeypatch.setattr(vd, "missing_project_packages", lambda: [])
    assert vd.main() == code
    out = capsys.readouterr().out
    assert ("todas na versão certa" in out) == (code == 0)


@pytest.mark.parametrize("script", PS_SCRIPTS, ids=lambda p: p.name)
def test_powershell_scripts_have_utf8_bom(script):
    # Sem BOM, o Windows PowerShell 5.1 lê o arquivo como ANSI e embaralha os acentos
    assert script.read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("script", PS_SCRIPTS, ids=lambda p: p.name)
def test_powershell_functions_are_not_glued_to_arguments(script):
    # 'Confirm-Step"texto"' passa no parser, mas falha na execução: o PowerShell procura um
    # comando chamado 'Confirm-Step"texto"'
    source = script.read_text(encoding="utf-8-sig")
    for name in re.findall(r"^function ([\w-]+)", source, flags=re.MULTILINE):
        assert not re.search(rf"{re.escape(name)}[\"'$]", source), name


def test_installer_is_wired_to_docs_and_checker():
    installer = (ROOT / "scripts" / "instalar.ps1").read_text(encoding="utf-8-sig")
    assert "verificar_dependencias.py" in installer
    assert 'run_local.ps1") -Testar' in installer
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "scripts\\instalar.ps1" in readme


# --- Teste de carga --------------------------------------------------------------


def test_load_test_percentile_and_summary():
    from scripts import load_test as lt

    assert lt.percentile([], 95) == 0.0
    assert lt.percentile([5, 1, 3, 2, 4], 50) == 3
    assert lt.percentile(list(range(1, 101)), 95) == 95
    samples = [{"ok": True, "ms": 10.0, "refused": True}, {"ok": True, "ms": 30.0}] + [
        {"ok": False, "ms": 999.0, "status": 500}
    ]
    summary = lt.summarize(samples, wall_s=2.0)
    assert summary["errors"] == 1 and summary["refused"] == 1
    assert summary["throughput_rps"] == 1.0 and summary["max_ms"] == 30.0  # erro fora da latência


def test_load_test_step_counts_errors_and_respects_concurrency():
    import asyncio

    import httpx

    from scripts import load_test as lt

    state = {"in_flight": 0, "peak": 0, "calls": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        call = state["calls"]  # lido antes do await: outras requisições mexem no contador
        state["in_flight"] += 1
        state["peak"] = max(state["peak"], state["in_flight"])
        await asyncio.sleep(0.01)
        state["in_flight"] -= 1
        status = 500 if call % 4 == 0 else 200
        return httpx.Response(status, json={"refused": False})

    async def go():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
            return await lt.run_step(client, "/ask", ["q1", "q2"], concurrency=3, total=20)

    result = asyncio.run(go())
    assert result["requests"] == 20 and result["errors"] == 5
    assert result["error_statuses"] == ["500"] and state["peak"] <= 3
    assert len(lt.load_questions()) >= 30  # usa o conjunto de desenvolvimento
