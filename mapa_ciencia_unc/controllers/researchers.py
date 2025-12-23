import numpy as np

from mapa_ciencia_unc.models.researcher import Researcher


async def get_similar_researchers(cuit: str, tag: str, model: str, n: int = 3):
    # 1. Get the target researcher and their specific vector
    target_researcher = await Researcher.find_one({"cuit": cuit})
    if not target_researcher:
        return []

    try:
        target_emb_obj = next(
            e for e in target_researcher.embeddings if e.tag == tag and e.model == model
        )
        target_vector = np.array(target_emb_obj.vector)
    except StopIteration:
        return []  # Or raise an error: specific embedding not found

    # 2. Fetch all candidates who have the matching tag/model
    # We fetch only the fields we need to keep memory usage low
    cursor = Researcher.find(
        {
            "cuit": {"$ne": cuit},
            "embeddings": {"$elemMatch": {"tag": tag, "model": model}},
        }
    )

    similarities = []

    async for researcher in cursor:
        # Find the specific embedding within the candidate's list
        candidate_emb = next(
            e for e in researcher.embeddings if e.tag == tag and e.model == model
        )
        candidate_vector = np.array(candidate_emb.vector)

        # 3. Compute Cosine Similarity using NumPy
        # Formula: (A dot B) / (norm(A) * norm(B))
        dot_product = np.dot(target_vector, candidate_vector)
        norm_target = np.linalg.norm(target_vector)
        norm_candidate = np.linalg.norm(candidate_vector)

        similarity = dot_product / (norm_target * norm_candidate)

        similarities.append({"researcher": researcher, "similarity": float(similarity)})

    # 4. Sort by similarity descending and return top N
    similarities.sort(key=lambda x: x["similarity"], reverse=True)

    return [
        {
            "name": r["researcher"].name,
            "last_name": r["researcher"].last_name,
            "research_center": r["researcher"].research_center,
            "researcher_id": str(r["researcher"].id),
        }
        for r in similarities[:n]
    ]
