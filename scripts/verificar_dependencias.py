"""Confere se as dependências fixadas no pyproject.toml estão instaladas, na versão certa.

Usado pelo ``scripts/instalar.ps1``, que roda este arquivo com o Python do ``.venv``. Imprime
uma linha por problema e termina com código 1 se houver algum; sem problemas, imprime um resumo.

    .venv\\Scripts\\python.exe scripts\\verificar_dependencias.py
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tomllib
from collections.abc import Callable, Iterable
from importlib import metadata
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
EXTRAS = ("dev", "ui")
# Pacotes de src/ que a API, a ingestão e a interface importam (instalação editável)
PROJECT_PACKAGES = ("core", "ingestion", "retrieval", "generation", "api", "ui")

_PIN_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?\s*==\s*([^\s;]+)")


def normalize(name: str) -> str:
    """Normaliza o nome do pacote como o pip faz (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def pinned_requirements(
    pyproject: Path = PYPROJECT, extras: Iterable[str] = EXTRAS
) -> dict[str, str]:
    """Nome normalizado -> versão de cada dependência fixada com ``==``."""
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
    specs = list(project.get("dependencies", []))
    optional = project.get("optional-dependencies", {})
    for extra in extras:
        specs += optional.get(extra, [])
    pins: dict[str, str] = {}
    for spec in specs:
        match = _PIN_RE.match(spec)
        if match:
            pins[normalize(match.group(1))] = match.group(2)
    return pins


def find_problems(
    pins: dict[str, str], version_of: Callable[[str], str] = metadata.version
) -> list[str]:
    """Lista as dependências ausentes ou numa versão diferente da fixada."""
    problems = []
    for name, expected in sorted(pins.items()):
        try:
            found = version_of(name)
        except metadata.PackageNotFoundError:
            problems.append(f"{name}: não instalado (esperado {expected})")
            continue
        if found != expected:
            problems.append(f"{name}: versão {found} instalada, esperado {expected}")
    return problems


def missing_project_packages(
    find_spec: Callable[[str], object | None] = importlib.util.find_spec,
) -> list[str]:
    return [name for name in PROJECT_PACKAGES if find_spec(name) is None]


def main() -> int:
    pins = pinned_requirements()
    problems = find_problems(pins)
    problems += [
        f"pacote '{name}' do projeto não encontrado (falta o 'pip install -e .')"
        for name in missing_project_packages()
    ]
    if problems:
        print("\n".join(problems))
        return 1
    print(f"{len(pins)} dependências fixadas, todas na versão certa")
    return 0


if __name__ == "__main__":
    sys.exit(main())
