"""Baixa a documentação oficial do FastAPI (licença MIT) numa versão fixa.

Uso:
    python scripts/download_fastapi_docs.py --version 0.115.5 --lang en

Extrai só os arquivos Markdown de docs/<lang>/docs/ para data/external/fastapi/<lang>/.
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://github.com/fastapi/fastapi/archive/refs/tags/{version}.tar.gz"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", default="0.115.5", help="Tag do repositório do FastAPI")
    parser.add_argument("--lang", default="en", help="Idioma da documentação (en, pt, es...)")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "external" / "fastapi")
    args = parser.parse_args(argv)

    url = URL.format(version=args.version)
    print(f"Baixando {url} ...")
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 (URL fixa do GitHub)
        payload = response.read()

    target = args.out / args.lang
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    prefix = f"fastapi-{args.version}/docs/{args.lang}/docs/"
    count = 0
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        for member in archive.getmembers():
            if not (
                member.isfile() and member.name.startswith(prefix) and member.name.endswith(".md")
            ):
                continue
            relative = Path(member.name[len(prefix) :])
            if relative.is_absolute() or ".." in relative.parts:
                continue  # proteção contra path traversal
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            extracted = archive.extractfile(member)
            if extracted is not None:
                destination.write_bytes(extracted.read())
                count += 1

    if count == 0:
        print(f"Nenhum arquivo encontrado para o idioma '{args.lang}'.", file=sys.stderr)
        return 1
    # Fica fora de `target` para não ser indexado junto com a documentação
    (args.out / f"FONTE-{args.lang}.txt").write_text(
        f"Fonte: {url}\nLicença: MIT (https://github.com/fastapi/fastapi/blob/master/LICENSE)\n",
        encoding="utf-8",
    )
    print(f"{count} arquivos Markdown salvos em {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
