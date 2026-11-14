# Pydantic: modelos de dados

O Pydantic é a biblioteca de validação de dados usada pelo FastAPI. Um modelo Pydantic é uma classe que herda de `BaseModel` e declara seus campos com anotações de tipo. Este guia usa a versão 2 do Pydantic.

## Declarando um modelo

```python
from pydantic import BaseModel

class Produto(BaseModel):
    nome: str
    preco: float
    em_estoque: bool = True
    tags: list[str] = []
```

Ao criar uma instância, o Pydantic valida e converte os dados de entrada. No modo padrão, chamado de modo flexível, o texto `"19.90"` é convertido para o número `19.9` no campo `preco`. Se um valor não puder ser convertido, a criação falha com uma `ValidationError` que descreve cada campo inválido.

## Modo estrito

Para recusar conversões automáticas e exigir exatamente o tipo declarado, ative o modo estrito com `ConfigDict(strict=True)` no modelo ou com `Field(strict=True)` em um campo específico. No modo estrito, o texto `"10"` não é aceito em um campo `int`.

## Criando modelos a partir de dados

| Método | O que faz |
| --- | --- |
| `Produto(**dados)` | Cria a partir de argumentos nomeados |
| `Produto.model_validate(dados)` | Valida um dicionário ou outro objeto |
| `Produto.model_validate_json(texto)` | Valida diretamente uma string JSON |

## Exportando modelos

```python
produto = Produto(nome="Caneta", preco="2.5")

produto.model_dump()                     # dicionário Python
produto.model_dump_json()                # string JSON
produto.model_dump(exclude_unset=True)   # só os campos definidos explicitamente
produto.model_copy(update={"preco": 3})  # cópia com campos alterados
```

O `model_dump(exclude_unset=True)` é útil em atualizações parciais, com o método PATCH: ele devolve apenas os campos que o cliente enviou, sem os valores padrão.

## Modelos aninhados

Um campo pode ter como tipo outro modelo, ou uma lista de modelos. O Pydantic valida toda a estrutura de forma recursiva, e o FastAPI documenta o esquema completo no OpenAPI.

```python
class Imagem(BaseModel):
    url: str
    largura: int

class ProdutoComImagens(BaseModel):
    nome: str
    imagens: list[Imagem] = []
```

## Configuração do modelo

A configuração de um modelo é feita com o atributo `model_config` e a classe `ConfigDict`:

- `extra="forbid"` rejeita campos que não foram declarados; o padrão, `extra="ignore"`, apenas os descarta.
- `from_attributes=True` permite criar o modelo a partir de atributos de um objeto, como uma linha retornada por um ORM. Na versão 1 do Pydantic essa opção se chamava `orm_mode`.
- `frozen=True` torna as instâncias imutáveis depois de criadas.
- `str_strip_whitespace=True` remove espaços no início e no fim de todos os campos de texto.

## Migração da versão 1 para a versão 2

Vários métodos foram renomeados na versão 2 do Pydantic: `dict()` virou `model_dump()`, `json()` virou `model_dump_json()`, `parse_obj()` virou `model_validate()`, o decorador `validator` virou `field_validator` e `root_validator` virou `model_validator`.
