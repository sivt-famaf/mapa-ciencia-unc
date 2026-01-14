import logging

from mapa_ciencia_unc.models.researcher import Researcher
from mapa_ciencia_unc.models.embedding import EmbeddingDocument
from mapa_ciencia_unc.services.embedding_index import get_embedding_index_manager
from beanie import PydanticObjectId

logger = logging.getLogger(__name__)


async def get_similar_researchers(
    cuit: str,
    tag: str,
    model: str,
    n: int = 3,
    summary_tag: str | None = None,
    summary_model: str | None = None,
):
    """
    Find researchers similar to the target researcher using FAISS-based vector search.

    This function uses the FAISS index for fast similarity search instead of
    manually computing cosine similarity for all researchers.

    Performance improvement: 10-100x faster than the old implementation,
    especially for large datasets.

    Args:
        cuit: CUIT identifier of the target researcher
        tag: Embedding tag to use for similarity search
        model: Embedding model to use for similarity search
        n: Number of similar researchers to return (default: 3)
        summary_tag: Optional tag for the summary to include (default: None)
        summary_model: Optional model for the summary to include (default: None)

    Returns:
        List of dictionaries containing similar researcher information:
        [
            {
                "name": "Juan",
                "last_name": "Pérez",
                "research_center": "CIEM",
                "research_area": "Inteligencia Artificial",
                "researcher_id": "507f1f77bcf86cd799439011",
                "summary": "Researcher working on..." (if summary_tag/model provided)
            },
            ...
        ]
        Returns empty list if target researcher or embedding not found.
    """
    # 1. Get the target researcher
    target_researcher = await Researcher.find_one({"cuit": cuit})
    if not target_researcher:
        logger.warning(f"Researcher with CUIT {cuit} not found")
        return []

    # 2. Get the target researcher's embedding from EmbeddingDocument collection
    embedding_doc = await EmbeddingDocument.find_one(
        EmbeddingDocument.researcher_id == target_researcher.id,
        EmbeddingDocument.tag == tag,
        EmbeddingDocument.model == model,
    )

    if not embedding_doc:
        logger.warning(
            f"Embedding not found for researcher {cuit} with tag='{tag}' and model='{model}'"
        )
        return []

    # 3. Use FAISS index manager for fast similarity search
    index_manager = get_embedding_index_manager()

    try:
        # Search for n+1 similar researchers (to account for the target researcher itself)
        similar_results = await index_manager.search_similar(
            query_vector=embedding_doc.vector,
            tag=tag,
            model=model,
            k=n + 1,  # Request n+1 to account for self
            include_distances=True,
        )
    except ValueError as e:
        logger.error(f"Error searching similar researchers: {e}")
        return []

    # 4. Filter out the target researcher and keep top n
    target_id_str = str(target_researcher.id)
    filtered_results = [
        (researcher_id, distance)
        for researcher_id, distance in similar_results
        if researcher_id != target_id_str
    ][:n]

    if not filtered_results:
        logger.info(f"No similar researchers found for {cuit}")
        return []

    # 5. Fetch researcher details from database
    researcher_ids = [PydanticObjectId(rid) for rid, _ in filtered_results]

    researchers = await Researcher.find(
        {"_id": {"$in": researcher_ids}}, fetch_links=False
    ).to_list()

    # Create a mapping for quick lookup
    researcher_map = {str(r.id): r for r in researchers}

    # 6. Build response maintaining the order from FAISS results
    result = []
    for researcher_id, distance in filtered_results:
        if researcher_id in researcher_map:
            researcher = researcher_map[researcher_id]

            # Build basic researcher info
            researcher_info = {
                "name": researcher.name,
                "last_name": researcher.last_name,
                "research_center": researcher.research_center,
                "researcher_id": researcher_id,
                "research_area": researcher.research_area,
                "academic_units": researcher.academic_units,
            }

            # Add summary if tag and model are provided
            if summary_tag and summary_model:
                summary_obj = next(
                    (
                        s
                        for s in researcher.summaries
                        if s.tag == summary_tag and s.model == summary_model
                    ),
                    None,
                )
                if summary_obj:
                    researcher_info["summary_brief"] = summary_obj.brief
                    researcher_info["summary_full"] = summary_obj.content
                else:
                    researcher_info["summary_brief"] = None
                    researcher_info["summary_full"] = None

            result.append(researcher_info)

    logger.info(f"Found {len(result)} similar researchers for {cuit}")
    return result
