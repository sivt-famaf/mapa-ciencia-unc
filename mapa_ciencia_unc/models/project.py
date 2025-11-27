from beanie import Document
from pydantic import BaseModel, Field
from datetime import datetime


class ProjectBase(BaseModel):
    convocatoria_id: str
    codigo_tramite: str
    titulo_proyecto: str
    resumen_proyecto: str
    palabrasclaves: str
    rol_grupo: str
    nombre: str
    apellido: str
    comision: str
    tema_periodo: str
    tema_periodo_ingles: str
    especialidad: str
    cuit: str
    fecha_alta: str
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
