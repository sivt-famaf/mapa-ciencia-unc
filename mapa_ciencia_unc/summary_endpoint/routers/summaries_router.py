from fastapi import APIRouter, Depends
from pathlib import Path

from ..models.schemas import SummaryRequest
from ..services.dataset_loader import load_dataset
from ..services.summary_generator import generate_researcher_summary
from ..utils.security import validate_internal_key
from ..config import SYSTEMS_DIR, USER_PROMPTS_DIR
from ..utils.swagger_docs import summary_description

router = APIRouter()

@router.post("/generate-summaries", description=summary_description,
             dependencies=[Depends(validate_internal_key)])
def generate_summaries(req: SummaryRequest):

    df = load_dataset(Path(req.dataset_path))

    df = df.head(req.limit)

    results = []

    for _, row in df.iterrows():
        info = row.get("info_completa", "")
        system_path = SYSTEMS_DIR / f"{req.system_name}.jinja"
        prompt_path = USER_PROMPTS_DIR / f"{req.prompt_name}.jinja"

        summary = generate_researcher_summary(
            info,
            system_instruction_path=system_path,
            prompt_path=prompt_path,
        )

        results.append({
            "id": row.get("id"),
            "summary": summary
        })

    return {"results": results}