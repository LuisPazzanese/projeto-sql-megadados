from typing import Annotated, Any

from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel

# Códigos de erro do MySQL tratados pela API
MYSQL_DUPLICADO = 1062  # violação de UNIQUE
MYSQL_FK_EM_USO = 1451  # linha referenciada por outra tabela (DELETE/UPDATE)
MYSQL_FK_INEXISTENTE = 1452  # FK aponta para linha que não existe


class Erro(BaseModel):
    detail: str = Field(description="Mensagem explicando o erro.")


def resposta_erro(descricao: str) -> dict[str, Any]:
    return {"model": Erro, "description": descricao}


class Paginacao(BaseModel):
    offset: int = Field(0, ge=0, description="Quantos registros pular.", examples=[0])
    limit: int = Field(
        20, ge=1, le=100, description="Máximo de registros retornados (1–100).", examples=[20]
    )


PaginacaoDep = Annotated[Paginacao, Query()]


def obter_ou_404[M: SQLModel](session: Session, modelo: type[M], id_: int, nome: str) -> M:
    obj = session.get(modelo, id_)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{nome} {id_} não encontrado")
    return obj


def commit_ou_erro(session: Session, erros: dict[int, tuple[int, str]]) -> None:
    """Faz commit; traduz violações de integridade do MySQL em respostas HTTP.

    `erros` mapeia código de erro do MySQL -> (status HTTP, mensagem).
    Deixar o banco validar (em vez de consultar antes) evita condições de corrida.
    """
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        codigo = exc.orig.args[0] if exc.orig is not None and exc.orig.args else None
        if codigo in erros:
            status_http, mensagem = erros[codigo]
            raise HTTPException(status_http, mensagem) from exc
        raise
