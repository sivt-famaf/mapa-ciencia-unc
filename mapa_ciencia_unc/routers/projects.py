from typing import List
from pathlib import Path

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.project import (
    Project,
    ProjectCreate,
    ProjectExtractedIntro,
    ProjectExtractedIntroCreate,
)
from mapa_ciencia_unc.models.researcher import Researcher


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


@router.post(
    "/extracted_intros/bulk", status_code=status.HTTP_201_CREATED, response_model=dict
)
async def create_extracted_intros_bulk(
    payload: List[ProjectExtractedIntroCreate], overwrite: bool = False
):
    created = 0
    skipped = 0
    for intro_data in payload:
        if not overwrite:
            existing = await ProjectExtractedIntro.find_one(
                {
                    "cuit": intro_data.cuit,
                    "codigo_tramite": intro_data.codigo_tramite,
                }
            )
            if existing:
                skipped += 1
                continue  # Skip existing entries

        # If overwrite is True, delete existing entry first
        await ProjectExtractedIntro.find(
            {
                "cuit": intro_data.cuit,
                "codigo_tramite": intro_data.codigo_tramite,
            }
        ).delete()

        intro_entry = ProjectExtractedIntro(**intro_data.model_dump())
        await intro_entry.insert()
        created += 1

    return {
        "created": created,
        "skipped": skipped,
    }


PROJECT_FILE_DIRECTORY = Path("./project_files").resolve()


@router.get("/download_project_file/")
async def download_file(reseacher_id: str, codigo_tramite: str):
    # get researcher cuit
    researcher = await Researcher.find_one({"_id": PydanticObjectId(reseacher_id)})
    if not researcher:
        raise HTTPException(status_code=404, detail="Researcher not found")

    cuit = researcher.cuit

    # find file name from ProjectExtractedIntro
    intro_entry = await ProjectExtractedIntro.find_one(
        {
            "cuit": cuit,
            "codigo_tramite": codigo_tramite,
        }
    )
    if not intro_entry:
        raise HTTPException(status_code=404, detail="File not found")

    filename = intro_entry.file_name
    file_path = PROJECT_FILE_DIRECTORY / filename

    # Security Check: Prevent Directory Traversal attacks
    if not str(file_path).startswith(str(PROJECT_FILE_DIRECTORY)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return_filename = f"{codigo_tramite}.{file_path.suffix.lstrip('.')}"

    # Return the file as a response
    return FileResponse(
        path=file_path,
        filename=return_filename,
        media_type="application/octet-stream",
    )
