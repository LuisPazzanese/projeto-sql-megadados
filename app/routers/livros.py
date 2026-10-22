from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response, status
from sqlmodel import Session, col, select

from app.core.database import SessionDep
from app.models.livro import (
    Genero,
    Livro,
    LivroCreate,
    LivroPublic,
    LivroPublicComAutor,
    LivroUpdate,
)
from app.routers.comum import (
    MYSQL_DUPLICADO,
    MYSQL_FK_INEXISTENTE,
    PaginacaoDep,
    commit_ou_erro,
    obter_ou_404,
    resposta_erro,
)

router = APIRouter(prefix="/livros", tags=["Livros"])

LivroId = Annotated[int, Path(ge=1, description="ID do livro.", examples=[1])]

NAO_ENCONTRADO = {404: resposta_erro("Livro não encontrado.")}
# 422 fica com o schema padrão do FastAPI (erros de validação); o caso de
# autor inexistente, que também responde 422, é citado na descrição das rotas.
CONFLITO_ISBN = {409: resposta_erro("Já existe um livro com esse ISBN.")}
AUTOR_INEXISTENTE = "Se `autor_id` não existir, responde 422."
# Tradução das violações de integridade do MySQL ao gravar um livro
ERROS_MYSQL = {
    MYSQL_DUPLICADO: (status.HTTP_409_CONFLICT, "Já existe um livro com esse ISBN"),
    MYSQL_FK_INEXISTENTE: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "autor_id não corresponde a nenhum autor cadastrado",
    ),
}


def _salvar(session: Session, livro: Livro) -> LivroPublic:
    session.add(livro)
    commit_ou_erro(session, ERROS_MYSQL)
    session.refresh(livro)
    return LivroPublic.model_validate(livro)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Criar livro",
    description=(
        "Cadastra um livro de um autor existente. O ISBN deve ser único (409). "
        f"{AUTOR_INEXISTENTE} O header `Location` aponta para o recurso criado."
    ),
    response_description="Livro criado.",
    responses=CONFLITO_ISBN,
)
def criar_livro(
    dados: LivroCreate, session: SessionDep, request: Request, response: Response
) -> LivroPublic:
    livro = _salvar(session, Livro.model_validate(dados))
    response.headers["Location"] = str(request.url_for("obter_livro", livro_id=livro.id))
    return livro


@router.get(
    "",
    summary="Listar livros",
    description="Lista livros ordenados por ID, com paginação e filtros opcionais combináveis.",
    response_description="Página de livros.",
)
def listar_livros(
    session: SessionDep,
    paginacao: PaginacaoDep,
    titulo: Annotated[
        str | None,
        Query(
            min_length=1,
            description="Filtra livros cujo título contém este texto.",
            examples=["Casmurro"],
        ),
    ] = None,
    autor_id: Annotated[
        int | None, Query(ge=1, description="Filtra pelos livros de um autor.", examples=[1])
    ] = None,
    genero: Annotated[
        Genero | None, Query(description="Filtra por gênero.", examples=[Genero.romance])
    ] = None,
    disponivel: Annotated[
        bool | None, Query(description="Filtra por disponibilidade.", examples=[True])
    ] = None,
) -> list[LivroPublic]:
    consulta = select(Livro)
    if titulo is not None:
        consulta = consulta.where(col(Livro.titulo).contains(titulo, autoescape=True))
    if autor_id is not None:
        consulta = consulta.where(Livro.autor_id == autor_id)
    if genero is not None:
        consulta = consulta.where(Livro.genero == genero)
    if disponivel is not None:
        consulta = consulta.where(Livro.disponivel == disponivel)
    consulta = consulta.order_by(col(Livro.id)).offset(paginacao.offset).limit(paginacao.limit)
    return [LivroPublic.model_validate(livro) for livro in session.exec(consulta)]


@router.get(
    "/{livro_id}",
    summary="Obter livro",
    description="Retorna um livro pelo ID, incluindo os dados do autor.",
    response_description="Livro encontrado.",
    responses=NAO_ENCONTRADO,
)
def obter_livro(livro_id: LivroId, session: SessionDep) -> LivroPublicComAutor:
    livro = obter_ou_404(session, Livro, livro_id, "Livro")
    return LivroPublicComAutor.model_validate(livro, update={"autor": livro.autor})


@router.put(
    "/{livro_id}",
    summary="Substituir livro",
    description=(
        "Substitui **todos** os dados do livro; campos com valor padrão omitidos "
        "(`genero`, `disponivel`) voltam ao padrão. Para alterar só alguns campos use PATCH. "
        f"{AUTOR_INEXISTENTE}"
    ),
    response_description="Livro atualizado.",
    responses={**NAO_ENCONTRADO, **CONFLITO_ISBN},
)
def substituir_livro(livro_id: LivroId, dados: LivroCreate, session: SessionDep) -> LivroPublic:
    livro = obter_ou_404(session, Livro, livro_id, "Livro")
    livro.sqlmodel_update(dados.model_dump())
    return _salvar(session, livro)


@router.patch(
    "/{livro_id}",
    summary="Alterar livro parcialmente",
    description=(
        "Altera apenas os campos enviados no corpo (ex.: marcar como indisponível). "
        f"{AUTOR_INEXISTENTE}"
    ),
    response_description="Livro atualizado.",
    responses={**NAO_ENCONTRADO, **CONFLITO_ISBN},
)
def alterar_livro(livro_id: LivroId, dados: LivroUpdate, session: SessionDep) -> LivroPublic:
    livro = obter_ou_404(session, Livro, livro_id, "Livro")
    livro.sqlmodel_update(dados.model_dump(exclude_unset=True))
    return _salvar(session, livro)


@router.delete(
    "/{livro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover livro",
    description="Remove o livro do acervo.",
    response_description="Livro removido (sem corpo).",
    responses=NAO_ENCONTRADO,
)
def remover_livro(livro_id: LivroId, session: SessionDep) -> None:
    livro = obter_ou_404(session, Livro, livro_id, "Livro")
    session.delete(livro)
    session.commit()
