from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.project import Project, ProjectCreate


router = APIRouter(
    prefix="/api/projects",
    tags=["projects"],
    dependencies=[Depends(require_auth)],
)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Project)
async def create_project(payload: ProjectCreate):
    project = Project(**payload.model_dump())
    await project.insert()
    return project


@router.get("", response_model=List[Project])
async def list_projects():
    projects = await Project.find_all().to_list()
    return projects


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    try:
        object_id = PydanticObjectId(project_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project id.",
        )

    project = await Project.find_one({"_id": object_id})
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return project
