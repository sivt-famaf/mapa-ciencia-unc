import logging
from typing import List

from beanie import PydanticObjectId

from mapa_ciencia_unc.models.researcher import Researcher


logger = logging.getLogger(__name__)


async def get_portfolio_context(
    researcher_ids: List[str],
    summary_tag: str = "complete",
    summary_model: str = "gemini-2.5-pro",
) -> List[str]:
    """
    Build a context text per researcher, preserving input order.

    Each text contains the researcher's full name, the keywords (areas)
    extracted from their summary, and the summary content itself.

    Args:
        researcher_ids: List of researcher ObjectId strings.
        summary_tag: Tag identifying which summary to use.
        summary_model: Model identifier for the summary to use.

    Returns:
        List of context strings, one per input ID, in the same order.
        If a researcher is not found or has no matching summary, their
        entry is an empty string.
    """
    object_ids = [PydanticObjectId(rid) for rid in researcher_ids]

    researchers = await Researcher.find(
        {"_id": {"$in": object_ids}},
        fetch_links=False,
    ).to_list()

    # Index by string ID for O(1) lookup when building the ordered result
    researcher_map = {str(r.id): r for r in researchers}

    contexts: List[str] = []
    for rid in researcher_ids:
        researcher = researcher_map.get(rid)
        if not researcher:
            logger.warning(f"Researcher {rid} not found")
            contexts.append("")
            continue

        summary_obj = next(
            (
                s
                for s in researcher.summaries
                if s.tag == summary_tag and s.model == summary_model
            ),
            None,
        )

        if not summary_obj:
            logger.warning(
                f"No summary with tag='{summary_tag}' model='{summary_model}' "
                f"for researcher {rid}"
            )
            contexts.append("")
            continue

        keywords = ", ".join(summary_obj.areas) if summary_obj.areas else "N/A"
        academic_units = ", ".join(researcher.academic_units) if researcher.academic_units else "N/A"

        context = (
            f"Name: {researcher.name} {researcher.last_name}\n"
            f"Research Area: {researcher.research_area or 'N/A'}\n"
            f"Highest Position: {researcher.highest_position}\n"
            f"Academic Units: {academic_units}\n"
            f"Last Project Title: {researcher.last_project_title or 'N/A'}\n"
            f"International Research Links: {'Sí' if researcher.international_research_links else 'No'}\n"
            f"Keywords: {keywords}\n"
            f"Summary: {summary_obj.content}"
        )
        contexts.append(context)

    return contexts
