from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, Field

from app.core.database import create_db_and_tables


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables()
    yield


DESCRICAO = """
API REST para gerenciar o acervo de uma **biblioteca**: autores e seus livros.

Construída com **FastAPI**, persistência em **MySQL** via ORM (**SQLModel**/SQLAlchemy).

* Use `POST` para criar, `GET` para consultar, `PUT` para substituir,
  `PATCH` para alterar parcialmente e `DELETE` para remover.
* Listagens são paginadas com `offset` e `limit`.
* Erros seguem o formato `{"detail": "..."}` com o código HTTP adequado
  (404 não encontrado, 409 conflito, 422 dados inválidos).
"""

TAGS = [
    {"name": "Autores", "description": "Cadastro de autores do acervo."},
    {"name": "Livros", "description": "Cadastro de livros, cada um ligado a um autor."},
    {"name": "Raiz", "description": "Ponto de entrada da API."},
]

app = FastAPI(
    title="API Biblioteca",
    summary="Microsserviço RESTful com ORM e MySQL (Projeto SQL — Megadados).",
    description=DESCRICAO,
    version="1.0.0",
    openapi_tags=TAGS,
    lifespan=lifespan,
)


@app.middleware("http")
async def cache_control(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Informa a cacheability de cada resposta (requisito REST).

    Leituras podem ser guardadas em cache, mas precisam ser revalidadas porque
    o banco pode mudar entre duas consultas; escritas nunca são cacheáveis.
    """
    response = await call_next(request)
    if "cache-control" not in response.headers:
        cacheavel = request.method in ("GET", "HEAD") and response.status_code == 200
        response.headers["Cache-Control"] = "no-cache" if cacheavel else "no-store"
    return response


class Indice(BaseModel):
    mensagem: str = Field(description="Boas-vindas.")
    documentacao: str = Field(description="URL da documentação interativa (Swagger UI).")
    recursos: dict[str, str] = Field(description="URIs das coleções disponíveis.")


@app.get(
    "/",
    tags=["Raiz"],
    summary="Índice da API",
    description="Retorna links para a documentação e para as coleções de recursos.",
)
def indice() -> Indice:
    return Indice(
        mensagem="Bem-vindo à API Biblioteca!",
        documentacao="/docs",
        recursos={},
    )
