from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response, status
from sqlmodel import col, select

from app.core.database import SessionDep
from app.models.autor import Autor, AutorCreate, AutorPublic, AutorUpdate
from app.models.livro import Livro, LivroPublic
from app.routers.comum import (
    MYSQL_FK_EM_USO,
    PaginacaoDep,
    commit_ou_erro,
    obter_ou_404,
    resposta_erro,
)

router = APIRouter(prefix="/autores", tags=["Autores"])

AutorId = Annotated[int, Path(ge=1, description="ID do autor.", examples=[1])]

NAO_ENCONTRADO = {404: resposta_erro("Autor não encontrado.")}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Criar autor",
    description="Cadastra um novo autor. O header `Location` aponta para o recurso criado.",
    response_description="Autor criado.",
)
def criar_autor(
    dados: AutorCreate, session: SessionDep, request: Request, response: Response
) -> AutorPublic:
    autor = Autor.model_validate(dados)
    session.add(autor)
    session.commit()
    session.refresh(autor)
    response.headers["Location"] = str(request.url_for("obter_autor", autor_id=autor.id))
    return AutorPublic.model_validate(autor)


@router.get(
    "",
    summary="Listar autores",
    description="Lista autores ordenados por ID, com paginação e filtros opcionais.",
    response_description="Página de autores.",
)
def listar_autores(
    session: SessionDep,
    paginacao: PaginacaoDep,
    nome: Annotated[
        str | None,
        Query(
            min_length=1,
            description="Filtra autores cujo nome contém este texto.",
            examples=["Machado"],
        ),
    ] = None,
    nacionalidade: Annotated[
        str | None,
        Query(min_length=1, description="Filtra por nacionalidade exata.", examples=["Brasileira"]),
    ] = None,
) -> list[AutorPublic]:
    consulta = select(Autor)
    if nome is not None:
        consulta = consulta.where(col(Autor.nome).contains(nome, autoescape=True))
    if nacionalidade is not None:
        consulta = consulta.where(Autor.nacionalidade == nacionalidade)
    consulta = consulta.order_by(col(Autor.id)).offset(paginacao.offset).limit(paginacao.limit)
    return [AutorPublic.model_validate(a) for a in session.exec(consulta)]


@router.get(
    "/{autor_id}",
    summary="Obter autor",
    description="Retorna um autor pelo ID.",
    response_description="Autor encontrado.",
    responses=NAO_ENCONTRADO,
)
def obter_autor(autor_id: AutorId, session: SessionDep) -> AutorPublic:
    return AutorPublic.model_validate(obter_ou_404(session, Autor, autor_id, "Autor"))


@router.get(
    "/{autor_id}/livros",
    summary="Listar livros do autor",
    description="Sub-recurso: livros de um autor, ordenados por ano de publicação.",
    response_description="Página de livros do autor.",
    responses=NAO_ENCONTRADO,
)
def listar_livros_do_autor(
    autor_id: AutorId, session: SessionDep, paginacao: PaginacaoDep
) -> list[LivroPublic]:
    obter_ou_404(session, Autor, autor_id, "Autor")
    consulta = (
        select(Livro)
        .where(Livro.autor_id == autor_id)
        .order_by(col(Livro.ano_publicacao), col(Livro.id))
        .offset(paginacao.offset)
        .limit(paginacao.limit)
    )
    return [LivroPublic.model_validate(livro) for livro in session.exec(consulta)]


@router.put(
    "/{autor_id}",
    summary="Substituir autor",
    description=(
        "Substitui **todos** os dados do autor. Campos opcionais omitidos voltam ao "
        "valor padrão (ex.: `nacionalidade` vira `null`). Para alterar só alguns campos use PATCH."
    ),
    response_description="Autor atualizado.",
    responses=NAO_ENCONTRADO,
)
def substituir_autor(autor_id: AutorId, dados: AutorCreate, session: SessionDep) -> AutorPublic:
    autor = obter_ou_404(session, Autor, autor_id, "Autor")
    autor.sqlmodel_update(dados.model_dump())
    session.add(autor)
    session.commit()
    session.refresh(autor)
    return AutorPublic.model_validate(autor)


@router.patch(
    "/{autor_id}",
    summary="Alterar autor parcialmente",
    description="Altera apenas os campos enviados no corpo.",
    response_description="Autor atualizado.",
    responses=NAO_ENCONTRADO,
)
def alterar_autor(autor_id: AutorId, dados: AutorUpdate, session: SessionDep) -> AutorPublic:
    autor = obter_ou_404(session, Autor, autor_id, "Autor")
    autor.sqlmodel_update(dados.model_dump(exclude_unset=True))
    session.add(autor)
    session.commit()
    session.refresh(autor)
    return AutorPublic.model_validate(autor)


@router.delete(
    "/{autor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover autor",
    description="Remove o autor. Não é permitido remover autores que ainda possuem livros (409).",
    response_description="Autor removido (sem corpo).",
    responses={
        **NAO_ENCONTRADO,
        409: resposta_erro("Autor possui livros cadastrados."),
    },
)
def remover_autor(autor_id: AutorId, session: SessionDep) -> None:
    autor = obter_ou_404(session, Autor, autor_id, "Autor")
    session.delete(autor)
    commit_ou_erro(
        session,
        {
            MYSQL_FK_EM_USO: (
                status.HTTP_409_CONFLICT,
                f"Autor {autor_id} possui livros cadastrados; remova-os antes",
            )
        },
    )
