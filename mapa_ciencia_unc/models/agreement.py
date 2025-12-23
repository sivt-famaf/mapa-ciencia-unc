from beanie import Document, Indexed
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Annotated

from mapa_ciencia_unc.models.constants import CUIT_FIELD


class AgreementBase(BaseModel):
    cuit: str = CUIT_FIELD
    nombre: str
    apellido: str
    descripcion: str
    tipo_produccion_tecnologica: str | None = None
    campo_aplicacion: str | None = None
    destinatario: str | None = None
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None


class AgreementCreate(AgreementBase):
    pass


class Agreement(AgreementBase, Document):
    created_at: datetime = Field(default_factory=datetime.now)
    cuit: Annotated[str, Indexed()] = AgreementBase.model_fields["cuit"]
