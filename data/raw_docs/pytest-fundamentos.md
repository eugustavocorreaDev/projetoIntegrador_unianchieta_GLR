# pytest: fundamentos

O pytest é o framework de testes mais usado em Python. Ele dispensa classes e métodos especiais: um teste é uma função comum que usa a instrução `assert` do próprio Python.

## Como o pytest encontra os testes

Ao rodar `pytest` na raiz do projeto, a ferramenta procura testes recursivamente seguindo estas convenções:

- arquivos com nome `test_*.py` ou `*_test.py`;
- funções cujo nome começa com `test`;
- métodos que começam com `test` dentro de classes cujo nome começa com `Test` e que não têm método `__init__`.

```python
# arquivo: tests/test_calculo.py
def somar(a, b):
    return a + b

def test_somar():
    assert somar(2, 3) == 5
```

## Mensagens de falha detalhadas

O pytest reescreve as instruções `assert` antes de executar os testes. Quando uma comparação falha, a saída mostra os valores dos dois lados e, no caso de listas, dicionários e textos, aponta exatamente onde eles diferem. Por isso não é preciso usar métodos como `assertEqual`.

## Opções úteis da linha de comando

| Opção | Efeito |
| --- | --- |
| `pytest -v` | Mostra o nome de cada teste executado |
| `pytest -q` | Saída resumida |
| `pytest -x` | Para na primeira falha |
| `pytest -k "login and not lento"` | Roda só os testes cujo nome corresponde à expressão |
| `pytest --lf` | Roda de novo só os testes que falharam na última execução |
| `pytest tests/test_api.py::test_health` | Roda um único teste |

## Testando exceções

Para verificar que um código levanta uma exceção, use `pytest.raises` como gerenciador de contexto. O argumento `match` confere a mensagem com uma expressão regular:

```python
import pytest

def test_divisao_por_zero():
    with pytest.raises(ZeroDivisionError, match="division"):
        1 / 0
```

## Parametrização

O marcador `pytest.mark.parametrize` executa o mesmo teste com vários conjuntos de entrada, e cada combinação aparece como um teste separado no relatório:

```python
@pytest.mark.parametrize("entrada,esperado", [(1, 2), (2, 4), (10, 20)])
def test_dobro(entrada, esperado):
    assert entrada * 2 == esperado
```

## Marcadores para pular testes

- `@pytest.mark.skip(reason="...")` pula o teste sempre.
- `@pytest.mark.skipif(condicao, reason="...")` pula o teste quando a condição é verdadeira, por exemplo em um sistema operacional específico.
- `@pytest.mark.xfail` indica que se espera que o teste falhe, como em um defeito conhecido ainda não corrigido.

Marcadores personalizados, como `@pytest.mark.lento`, devem ser registrados na opção `markers` da configuração do pytest, no `pyproject.toml` ou no `pytest.ini`. Com a opção `--strict-markers`, um marcador não registrado faz a execução falhar, o que evita erros de digitação.

## Configuração no pyproject.toml

A configuração do pytest pode ficar na seção `[tool.pytest.ini_options]` do `pyproject.toml`, com opções como `testpaths`, para indicar onde estão os testes, e `addopts`, para acrescentar opções padrão a toda execução.
