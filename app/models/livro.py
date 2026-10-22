from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import field_validator, model_validator
from sqlalchemy import func
from sqlmodel import Field, Relationship, SQLModel

from app.models.autor import Autor, AutorPublic
from app.models.comum import rejeitar_nulos

ISBN13 = r"^\d{13}$"


class Genero(StrEnum):
    # Nome == valor: o SQLAlchemy grava o *nome* do membro na coluna ENUM do MySQL.
    ficcao = "ficcao"
    ficcao_cientifica = "ficcao_cientifica"
    fantasia = "fantasia"
    romance = "romance"
    misterio = "misterio"
    poesia = "poesia"
    biografia = "biografia"
    historia = "historia"
    tecnico = "tecnico"
    infantil = "infantil"
    outro = "outro"


def _validar_ano(valor: int | None) -> int | None:
    if valor is not None and valor > date.today().year:
        raise ValueError("ano_publicacao não pode estar no futuro")
    return valor


class LivroBase(SQLModel):
    titulo: str = Field(
        min_length=1,
        max_length=200,
        index=True,
        description="Título do livro.",
        schema_extra={"examples": ["Dom Casmurro"]},
    )
    isbn: str = Field(
        unique=True,
        max_length=13,
        description="ISBN-13 (somente os 13 dígitos). Único no acervo.",
        schema_extra={"pattern": ISBN13, "examples": ["9788535910667"]},
    )
    ano_publicacao: int = Field(
        ge=1450,
        description="Ano da publicação (1450 até o ano atual).",
        schema_extra={"examples": [1899]},
    )
    paginas: int = Field(
        ge=1, le=100_000, description="Número de páginas.", schema_extra={"examples": [256]}
    )
    preco: Decimal = Field(
        ge=0,
        max_digits=8,
        decimal_places=2,
        description="Preço em reais, até 2 casas decimais.",
        schema_extra={"examples": ["39.90"]},
    )
    genero: Genero = Field(
        default=Genero.outro,
        description="Gênero literário.",
        schema_extra={"examples": [Genero.romance]},
    )
    disponivel: bool = Field(
        default=True,
        description="Se o exemplar está disponível para empréstimo.",
        schema_extra={"examples": [True]},
    )
    autor_id: int = Field(
        foreign_key="autor.id",
        ondelete="RESTRICT",
        index=True,
        description="ID do autor do livro (deve existir).",
        schema_extra={"examples": [1]},
    )

    validar_ano = field_validator("ano_publicacao")(_validar_ano)


class Livro(LivroBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    criado_em: datetime | None = Field(
        default=None, nullable=False, sa_column_kwargs={"server_default": func.now()}
    )
    atualizado_em: datetime | None = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )

    # Só o lado N:1. Sem coleção em Autor, o ORM não tenta mexer nos livros ao
    # remover um autor, e o MySQL aplica o ON DELETE RESTRICT (-> HTTP 409).
    autor: Autor = Relationship()


class LivroCreate(LivroBase):
    """Dados para criar (POST) ou substituir (PUT) um livro."""


class LivroUpdate(SQLModel):
    """Alteração parcial (PATCH): envie só os campos que deseja mudar."""

    titulo: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Novo título.",
        schema_extra={"examples": ["Dom Casmurro (edição comentada)"]},
    )
    isbn: str | None = Field(
        default=None,
        max_length=13,
        description="Novo ISBN-13.",
        schema_extra={"pattern": ISBN13, "examples": ["9788535910667"]},
    )
    ano_publicacao: int | None = Field(
        default=None, ge=1450, description="Novo ano de publicação.", schema_extra={"examples": [1900]}
    )
    paginas: int | None = Field(
        default=None, ge=1, le=100_000, description="Novo número de páginas.", schema_extra={"examples": [300]}
    )
    preco: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=8,
        decimal_places=2,
        description="Novo preço.",
        schema_extra={"examples": ["29.90"]},
    )
    genero: Genero | None = Field(
        default=None, description="Novo gênero.", schema_extra={"examples": [Genero.romance]}
    )
    disponivel: bool | None = Field(
        default=None, description="Nova disponibilidade.", schema_extra={"examples": [False]}
    )
    autor_id: int | None = Field(
        default=None, description="Novo autor (deve existir).", schema_extra={"examples": [1]}
    )

    validar_ano = field_validator("ano_publicacao")(_validar_ano)

    @model_validator(mode="after")
    def _obrigatorios_nao_nulos(self) -> Self:
        rejeitar_nulos(self, *self.__class__.model_fields)
        return self


class LivroPublic(LivroBase):
    id: int = Field(description="Identificador do livro.", schema_extra={"examples": [1]})
    criado_em: datetime = Field(description="Data/hora de criação do registro.")
    atualizado_em: datetime = Field(description="Data/hora da última alteração.")


class LivroPublicComAutor(LivroPublic):
    autor: AutorPublic = Field(description="Dados completos do autor.")
