from datetime import date, datetime
from typing import Self

from pydantic import field_validator, model_validator
from sqlalchemy import func
from sqlmodel import Field, SQLModel

from app.models.comum import rejeitar_nulos


def _validar_nascimento(valor: date | None) -> date | None:
    if valor is not None and valor > date.today():
        raise ValueError("data_nascimento não pode estar no futuro")
    return valor


class AutorBase(SQLModel):
    nome: str = Field(
        min_length=1,
        max_length=120,
        index=True,
        description="Nome completo do autor.",
        schema_extra={"examples": ["Machado de Assis"]},
    )
    nacionalidade: str | None = Field(
        default=None,
        max_length=60,
        description="Nacionalidade do autor (opcional).",
        schema_extra={"examples": ["Brasileira"]},
    )
    data_nascimento: date = Field(
        description="Data de nascimento (AAAA-MM-DD). Não pode estar no futuro.",
        schema_extra={"examples": ["1839-06-21"]},
    )

    validar_nascimento = field_validator("data_nascimento")(_validar_nascimento)


class Autor(AutorBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    criado_em: datetime | None = Field(
        default=None, nullable=False, sa_column_kwargs={"server_default": func.now()}
    )
    atualizado_em: datetime | None = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )


class AutorCreate(AutorBase):
    """Dados para criar (POST) ou substituir (PUT) um autor."""


class AutorUpdate(SQLModel):
    """Alteração parcial (PATCH): envie só os campos que deseja mudar."""

    nome: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Novo nome do autor.",
        schema_extra={"examples": ["Joaquim Maria Machado de Assis"]},
    )
    nacionalidade: str | None = Field(
        default=None,
        max_length=60,
        description="Nova nacionalidade (envie `null` para apagar).",
        schema_extra={"examples": ["Brasileira"]},
    )
    data_nascimento: date | None = Field(
        default=None,
        description="Nova data de nascimento (AAAA-MM-DD).",
        schema_extra={"examples": ["1839-06-21"]},
    )

    validar_nascimento = field_validator("data_nascimento")(_validar_nascimento)

    @model_validator(mode="after")
    def _obrigatorios_nao_nulos(self) -> Self:
        rejeitar_nulos(self, "nome", "data_nascimento")
        return self


class AutorPublic(AutorBase):
    id: int = Field(description="Identificador do autor.", schema_extra={"examples": [1]})
    criado_em: datetime = Field(description="Data/hora de criação do registro.")
    atualizado_em: datetime = Field(description="Data/hora da última alteração.")
