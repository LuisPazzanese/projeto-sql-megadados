from sqlmodel import SQLModel


def rejeitar_nulos(modelo: SQLModel, *campos: str) -> None:
    """Impede `null` explícito em campos obrigatórios de um PATCH.

    Nos schemas de alteração parcial todo campo é opcional (pode ser omitido),
    mas enviar `null` para uma coluna NOT NULL deve ser erro de validação (422),
    não um erro do banco.
    """
    nulos = [c for c in campos if c in modelo.model_fields_set and getattr(modelo, c) is None]
    if nulos:
        raise ValueError(f"campos obrigatórios não podem ser null: {', '.join(nulos)}")
