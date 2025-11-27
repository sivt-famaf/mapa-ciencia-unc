from beanie import Document
from pydantic import BaseModel, Field
from datetime import datetime


class ProjectBase(BaseModel):
    cuit: str
    convocatoria_id: str | None = None
    codigo_tramite: str | None = None
    titulo_proyecto: str | None = None
    resumen_proyecto: str | None = None
    palabrasclaves: str | None = None
    rol_grupo: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    comision: str | None = None
    tema_periodo: str | None = None
    tema_periodo_ingles: str | None = None
    especialidad: str | None = None
    fecha_alta: str | None = None
    estado_tramie: str | None = None
    convocatoria: str | None = None
    objeto_evaluacion: str | None = None
    grupo_oe: str | None = None
    postulante: str | None = None
    rol: str | None = None


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase, Document):
    created_at: datetime = Field(default_factory=datetime.now)
