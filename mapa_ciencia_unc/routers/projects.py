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
    if await Project.find_one(Project.codigo_tramite == payload.codigo_tramite):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project with this codigo_tramite already exists.",
        )
    project = Project(**payload.model_dump())
    await project.insert()
    return project


@router.post("/bulk", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_projects_bulk(payload: List[ProjectCreate]):
    created_projects = []
    failed_projects = []
    for project_data in payload:
        try:
            existing = await Project.find_one(project_data.model_dump())
            if existing:
                failed_projects.append(
                    {
                        "codigo_tramite": project_data.codigo_tramite,
                        "error": "This project already exists.",
                    }
                )
                continue  # Skip existing projects

            project = Project(**project_data.model_dump())
            await project.insert()
            created_projects.append(project)
        except Exception as e:
            failed_projects.append(
                {
                    "codigo_tramite": project_data.codigo_tramite,
                    "error": str(e),
                }
            )

    return {
        "created": created_projects,
        "failed": failed_projects,
    }


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
