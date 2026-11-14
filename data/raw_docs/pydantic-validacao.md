# Pydantic: validação personalizada

As anotações de tipo resolvem a maior parte das validações, mas regras de negócio costumam exigir verificações próprias. O Pydantic oferece restrições declarativas com `Field` e validadores escritos em Python.

## Restrições com Field

```python
from pydantic import BaseModel, Field

class Usuario(BaseModel):
    nome: str = Field(min_length=2, max_length=50)
    idade: int = Field(ge=0, le=130)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+$")
```

As restrições numéricas são `gt`, `ge`, `lt` e `le`. Para textos e listas, use `min_length` e `max_length`. O argumento `pattern` exige que o texto corresponda a uma expressão regular. Essas restrições também aparecem no esquema JSON gerado para a documentação.

## Validadores de campo

Para uma regra que não cabe nas restrições prontas, use o decorador `field_validator`:

```python
from pydantic import BaseModel, field_validator

class Cadastro(BaseModel):
    nome_completo: str

    @field_validator("nome_completo")
    @classmethod
    def precisa_de_sobrenome(cls, valor: str) -> str:
        # Levantar ValueError gera um erro de validação para este campo
        if " " not in valor.strip():
            raise ValueError("informe nome e sobrenome")
        return valor.title()
```

O validador recebe o valor já convertido para o tipo do campo e deve retornar o valor final, que pode ser transformado, como no exemplo, em que o nome é colocado em formato de título. Um `ValueError` ou um `AssertionError` levantado dentro do validador é convertido automaticamente em uma `ValidationError`.

Com `field_validator("campo", mode="before")`, o validador roda antes da conversão de tipo e recebe o dado bruto, o que permite, por exemplo, transformar uma string separada por vírgulas em uma lista.

## Validadores de modelo

Quando a regra envolve mais de um campo, use `model_validator`. No modo `after`, o método recebe a instância já validada e deve retorná-la:

```python
from pydantic import BaseModel, model_validator

class Periodo(BaseModel):
    inicio: int
    fim: int

    @model_validator(mode="after")
    def fim_depois_do_inicio(self):
        if self.fim < self.inicio:
            raise ValueError("fim deve ser maior ou igual ao início")
        return self
```

## Tratando ValidationError

```python
from pydantic import ValidationError

try:
    Periodo(inicio=10, fim=2)
except ValidationError as erro:
    for problema in erro.errors():
        print(problema["loc"], problema["msg"])
```

O método `errors()` devolve uma lista de dicionários. Cada dicionário traz a localização do problema em `loc`, a mensagem em `msg` e o tipo do erro em `type`. No FastAPI, essa mesma estrutura aparece no campo `detail` das respostas com status 422.

## Aliases

O argumento `alias` de `Field` define o nome usado na entrada e na saída de dados, por exemplo `Field(alias="dataNascimento")` para aceitar JSON em camelCase mantendo o atributo Python em snake_case. Para aceitar também o nome do atributo na entrada, ative `populate_by_name=True` no `ConfigDict`. Na exportação, use `model_dump(by_alias=True)` para gerar as chaves com os aliases.
