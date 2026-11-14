# pytest: fixtures

Fixtures são funções que preparam o que um teste precisa, como dados, conexões ou objetos configurados, e opcionalmente limpam tudo depois. Um teste recebe uma fixture simplesmente declarando um parâmetro com o nome dela.

## Declarando e usando uma fixture

```python
import pytest

@pytest.fixture
def carrinho():
    return {"itens": [], "total": 0}

def test_carrinho_comeca_vazio(carrinho):
    assert carrinho["itens"] == []
```

Fixtures podem depender de outras fixtures, também declarando-as como parâmetros. O pytest resolve essa cadeia e cria cada fixture na ordem certa.

## Limpeza com yield

Para executar código de encerramento, a fixture usa `yield` no lugar de `return`. Tudo o que vem depois do `yield` roda quando o teste termina, mesmo que ele tenha falhado:

```python
@pytest.fixture
def conexao():
    con = abrir_conexao()
    yield con
    # Encerramento: executado depois do teste
    con.close()
```

## Escopo

O argumento `scope` define por quanto tempo a fixture é reaproveitada:

| Escopo | A fixture é criada |
| --- | --- |
| `function` (padrão) | uma vez por teste |
| `class` | uma vez por classe de testes |
| `module` | uma vez por arquivo de testes |
| `package` | uma vez por pacote |
| `session` | uma única vez em toda a execução |

Escopos maiores economizam tempo em preparações caras, como subir um banco de dados de teste, mas exigem cuidado: um teste que altera o objeto compartilhado pode afetar os testes seguintes.

## Compartilhando fixtures com conftest.py

Fixtures definidas em um arquivo `conftest.py` ficam disponíveis para todos os testes da mesma pasta e das subpastas, sem nenhuma importação. Um projeto pode ter vários arquivos `conftest.py`, um em cada nível de pastas.

## Fixtures automáticas

Com `@pytest.fixture(autouse=True)`, a fixture é aplicada a todos os testes do seu alcance sem precisar ser declarada como parâmetro, o que é útil para restaurar um estado global antes de cada teste.

## Fixtures parametrizadas

Uma fixture pode ser criada várias vezes com valores diferentes usando `params`. Os testes que a usam rodam uma vez para cada valor, que a fixture lê em `request.param`:

```python
@pytest.fixture(params=["sqlite", "postgres"])
def banco(request):
    return request.param
```

## Fixtures embutidas mais usadas

- `tmp_path`: um diretório temporário exclusivo para o teste, como objeto `pathlib.Path`.
- `monkeypatch`: troca atributos, variáveis de ambiente e itens de dicionários durante o teste, com `setattr`, `setenv` e `delenv`. Tudo é desfeito automaticamente quando o teste termina.
- `capsys`: captura o que foi impresso; o método `readouterr()` devolve a saída padrão e a saída de erro.
- `caplog`: captura os registros feitos com o módulo `logging`.
