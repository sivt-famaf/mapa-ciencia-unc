from beanie import Document, Indexed
from pydantic import BaseModel, Field
from datetime import datetime
from mapa_ciencia_unc.models.constants import CUIT_FIELD
from typing import List, Annotated


class ProjectBase(BaseModel):
    cuit: str = CUIT_FIELD
    convocatoria_id: str
    codigo_tramite: str
    titulo_proyecto: str
    resumen_proyecto: str
    palabrasclaves: List[str] = []
    rol_grupo: str
    nombre: str
    apellido: str
    comision: str
    tema_periodo: str
    tema_periodo_ingles: str | None = None
    especialidad: str | None = None
    fecha_alta: datetime
    estado_tramie: str
    convocatoria: str
    objeto_evaluacion: str
    grupo_oe: str
    postulante: str
    rol: str


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase, Document):
    created_at: datetime = Field(default_factory=datetime.now)
    codigo_tramite: Annotated[str, Indexed()] = ProjectBase.model_fields[
        "codigo_tramite"
    ]
