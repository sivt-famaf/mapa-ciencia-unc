from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from mapa_ciencia_unc.auth import require_auth
from mapa_ciencia_unc.models.agreement import Agreement, AgreementCreate


router = APIRouter(
    prefix="/api/agreements",
    tags=["agreements"],
    dependencies=[Depends(require_auth)],
)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Agreement)
async def create_agreement(payload: AgreementCreate):
    """Create a single agreement."""
    # Check for existing agreement with same CUIT and descripcion
    existing = await Agreement.find_one(
        {
            "cuit": payload.cuit,
            "descripcion": payload.descripcion,
        }
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agreement with this CUIT and description already exists.",
        )

    agreement = Agreement(**payload.model_dump())
    await agreement.insert()
    return agreement


@router.post("/bulk", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_agreements_bulk(payload: List[AgreementCreate]):
    """Create multiple agreements in bulk."""
    created_agreements = []
    failed_agreements = []

    for agreement_data in payload:
        try:
            # Check if agreement already exists (by CUIT and descripcion)
            existing = await Agreement.find_one(
                {
                    "cuit": agreement_data.cuit,
                    "descripcion": agreement_data.descripcion,
                }
            )
            if existing:
                failed_agreements.append(
                    {
                        "cuit": agreement_data.cuit,
                        "nombre": agreement_data.nombre,
                        "apellido": agreement_data.apellido,
                        "error": "This agreement already exists.",
                    }
                )
                continue  # Skip existing agreements

            agreement = Agreement(**agreement_data.model_dump())
            await agreement.insert()
            created_agreements.append(agreement)
        except Exception as e:
            failed_agreements.append(
                {
                    "cuit": agreement_data.cuit,
                    "nombre": agreement_data.nombre,
                    "apellido": agreement_data.apellido,
                    "error": str(e),
                }
            )

    return {
        "created": created_agreements,
        "failed": failed_agreements,
        "summary": {
            "total": len(payload),
            "created_count": len(created_agreements),
            "failed_count": len(failed_agreements),
        },
    }


@router.get("", response_model=List[Agreement])
async def list_agreements():
    """List all agreements."""
    agreements = await Agreement.find_all().to_list()
    return agreements


@router.get("/{agreement_id}", response_model=Agreement)
async def get_agreement(agreement_id: str):
    """Get a specific agreement by ID."""
    try:
        object_id = PydanticObjectId(agreement_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agreement id.",
        )

    agreement = await Agreement.find_one({"_id": object_id})
    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found.",
        )

    return agreement


@router.get("/by-cuit/{cuit}", response_model=List[Agreement])
async def get_agreements_by_cuit(cuit: str):
    """Get all agreements for a specific CUIT."""
    agreements = await Agreement.find({"cuit": cuit}).to_list()
    return agreements
