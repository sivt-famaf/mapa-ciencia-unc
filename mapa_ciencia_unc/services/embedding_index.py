"""
FAISS-based embedding index manager for fast similarity search.

This service manages in-memory FAISS indexes for efficient vector similarity search.
Each (tag, model) combination gets its own index loaded from the EmbeddingDocument collection.
"""

import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import faiss
import numpy as np

from mapa_ciencia_unc.models.embedding import EmbeddingDocument

logger = logging.getLogger(__name__)


class EmbeddingIndexManager:
    """
    Manages FAISS indexes for fast similarity search.

    One index per (tag, model) combination. Indexes are loaded into memory
    on demand and can be persisted to disk for faster startup.

    Index Types:
    - Small dataset (<10k vectors): IndexFlatL2 - Exact search, no training needed
    - Medium dataset (10k-1M): IndexIVFFlat - Approximate search, faster
    - Large dataset (>1M): IndexIVFPQ - Compressed, memory efficient

    Attributes:
        indexes: Dictionary mapping (tag, model) to FAISS index
        id_mappings: Dictionary mapping (tag, model) to list of researcher IDs
                    (index position -> researcher_id)
        loaded_at: Dictionary tracking when each index was loaded
    """

    def __init__(self):
        """Initialize empty index manager."""
        self.indexes: Dict[Tuple[str, str], faiss.Index] = {}
        self.id_mappings: Dict[Tuple[str, str], List[str]] = {}
        self.loaded_at: Dict[Tuple[str, str], datetime] = {}
        logger.info("EmbeddingIndexManager initialized")

    async def load_index(self, tag: str, model: str) -> None:
        """
        Load embeddings from MongoDB and build FAISS index.

        Queries all embeddings for the given (tag, model) combination,
        builds a numpy array of vectors, creates the appropriate FAISS index,
        and caches it in memory with the researcher ID mapping.

        Args:
            tag: Tag identifier for the embeddings
            model: Model identifier for the embeddings

        Raises:
            ValueError: If no embeddings found for the given tag and model
        """
        key = (tag, model)

        logger.info(f"Loading FAISS index for tag='{tag}', model='{model}'")

        # Query all embeddings for this (tag, model)
        pipeline = [
            {"$match": {"tag": tag, "model": model}},
            {"$sort": {"created_at": -1}},
            {
                "$group": {
                    "_id": "$researcher_id",
                    "vector": {"$first": "$vector"},
                    "created_at": {"$first": "$created_at"},
                }
            },
        ]

        embedding_results = await EmbeddingDocument.aggregate(pipeline).to_list()

        if not embedding_results:
            available = await get_all_embedding_tags_models()
            available_str = ", ".join(
                f"(tag='{t}', model='{m}')" for t, m in available
            ) if available else "none"
            raise ValueError(
                f"No embeddings found for tag='{tag}' and model='{model}'. "
                f"Available combinations: {available_str}"
            )

        # Extract vectors and researcher IDs
        vectors = []
        researcher_ids = []

        for result in embedding_results:
            vectors.append(result["vector"])
            researcher_ids.append(str(result["_id"]))

        # Convert to numpy array
        vectors_array = np.array(vectors, dtype=np.float32)
        num_vectors, dimensions = vectors_array.shape

        logger.info(
            f"Loaded {num_vectors} vectors with {dimensions} dimensions "
            f"for tag='{tag}', model='{model}'"
        )

        # Create appropriate FAISS index based on dataset size
        index = self._create_index(vectors_array, num_vectors, dimensions)

        # Store index, mappings, and timestamp
        self.indexes[key] = index
        self.id_mappings[key] = researcher_ids
        self.loaded_at[key] = datetime.now()

        logger.info(
            f"FAISS index created successfully: {num_vectors} vectors, "
            f"index type: {type(index).__name__}"
        )

    def _create_index(
        self, vectors: np.ndarray, num_vectors: int, dimensions: int
    ) -> faiss.Index:
        """
        Create appropriate FAISS index based on dataset size.

        Args:
            vectors: Numpy array of embedding vectors
            num_vectors: Number of vectors
            dimensions: Vector dimensionality

        Returns:
            Configured FAISS index
        """
        if num_vectors < 10000:
            # Small dataset: Use exact search
            logger.info("Using IndexFlatL2 (exact search) for small dataset")
            index = faiss.IndexFlatL2(dimensions)
            index.add(vectors)

        elif num_vectors < 1000000:
            # Medium dataset: Use IVF index for faster approximate search
            logger.info("Using IndexIVFFlat (approximate search) for medium dataset")

            # Number of clusters (nlist) - typically sqrt(N) to 4*sqrt(N)
            nlist = min(int(np.sqrt(num_vectors) * 2), num_vectors // 10)
            nlist = max(nlist, 10)  # At least 10 clusters

            # Create quantizer (used to partition the space)
            quantizer = faiss.IndexFlatL2(dimensions)

            # Create IVF index
            index = faiss.IndexIVFFlat(quantizer, dimensions, nlist)

            # Train the index (required for IVF)
            logger.info(f"Training IVF index with {nlist} clusters...")
            index.train(vectors)

            # Add vectors
            index.add(vectors)

            # Set search parameters (nprobe = number of clusters to visit)
            # Higher nprobe = more accurate but slower
            index.nprobe = min(nlist // 2, 50)

        else:
            # Large dataset: Use IVF with product quantization for compression
            logger.info("Using IndexIVFPQ (compressed) for large dataset")

            nlist = min(int(np.sqrt(num_vectors) * 4), num_vectors // 10)
            nlist = max(nlist, 100)  # At least 100 clusters

            # Product quantization parameters
            m = 8  # Number of sub-quantizers
            nbits = 8  # Bits per sub-quantizer

            # Create quantizer
            quantizer = faiss.IndexFlatL2(dimensions)

            # Create IVF+PQ index
            index = faiss.IndexIVFPQ(quantizer, dimensions, nlist, m, nbits)

            # Train and add
            logger.info(f"Training IVF+PQ index with {nlist} clusters...")
            index.train(vectors)
            index.add(vectors)

            # Set search parameters
            index.nprobe = min(nlist // 2, 100)

        return index

    async def search_similar(
        self,
        query_vector: List[float],
        tag: str,
        model: str,
        k: int = 10,
        include_distances: bool = True,
    ) -> List[Tuple[str, float]] | List[str]:
        """
        Find k most similar researchers to query_vector.

        Args:
            query_vector: Query embedding vector
            tag: Tag identifier for the index to search
            model: Model identifier for the index to search
            k: Number of similar researchers to return (default: 10)
            include_distances: Whether to include distances in results (default: True)

        Returns:
            If include_distances=True: List of (researcher_id, distance) tuples
            If include_distances=False: List of researcher_id strings
            Sorted by similarity (closest first)

        Raises:
            ValueError: If index not loaded for the given tag and model
        """
        key = (tag, model)

        # Check if index is loaded, if not, load it
        if key not in self.indexes:
            logger.info(
                f"Index not loaded for tag='{tag}', model='{model}', loading now..."
            )
            await self.load_index(tag, model)

        index = self.indexes[key]
        if index.d != len(query_vector):
            raise ValueError("Query vector must have same dimensionality as index")
        id_mapping = self.id_mappings[key]

        # Convert query vector to numpy array
        query_array = np.array([query_vector], dtype=np.float32)

        # Ensure k doesn't exceed number of vectors in index
        k = min(k, index.ntotal)

        # Search with FAISS
        distances, indices = index.search(query_array, k)

        # Map positions to researcher IDs
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(id_mapping):  # Valid index
                researcher_id = id_mapping[idx]
                if include_distances:
                    results.append((researcher_id, float(distance)))
                else:
                    results.append(researcher_id)

        logger.debug(
            f"Found {len(results)} similar researchers for tag='{tag}', model='{model}'"
        )

        return results

    async def rebuild_index(self, tag: str, model: str) -> None:
        """
        Rebuild index after new embeddings added.

        This method reloads the index from MongoDB, useful when new embeddings
        have been added or existing ones modified.

        Args:
            tag: Tag identifier for the index to rebuild
            model: Model identifier for the index to rebuild
        """
        key = (tag, model)

        logger.info(f"Rebuilding index for tag='{tag}', model='{model}'")

        # Remove old index if it exists
        if key in self.indexes:
            del self.indexes[key]
            del self.id_mappings[key]
            del self.loaded_at[key]

        # Load fresh index
        await self.load_index(tag, model)

        logger.info(f"Index rebuilt successfully for tag='{tag}', model='{model}'")

    async def save_index_to_disk(
        self, tag: str, model: str, directory: str | Path
    ) -> None:
        """
        Persist FAISS index to disk for faster startup.

        Saves both the FAISS index and the researcher ID mapping to disk.

        Args:
            tag: Tag identifier for the index to save
            model: Model identifier for the index to save
            directory: Directory path to save index files

        Raises:
            ValueError: If index not loaded for the given tag and model
        """
        key = (tag, model)

        if key not in self.indexes:
            raise ValueError(f"No index loaded for tag='{tag}' and model='{model}'")

        # Create directory if it doesn't exist
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        # Create safe filenames
        safe_tag = tag.replace("/", "_").replace(" ", "_")
        safe_model = model.replace("/", "_").replace(" ", "_")

        index_file = directory / f"index_{safe_tag}_{safe_model}.faiss"
        mapping_file = directory / f"mapping_{safe_tag}_{safe_model}.pkl"

        # Save FAISS index
        faiss.write_index(self.indexes[key], str(index_file))

        # Save ID mapping using pickle
        with open(mapping_file, "wb") as f:
            pickle.dump(self.id_mappings[key], f)

        logger.info(f"Index saved to disk: {index_file} and {mapping_file}")

    async def load_index_from_disk(
        self, tag: str, model: str, directory: str | Path
    ) -> bool:
        """
        Load persisted FAISS index from disk.

        Loads both the FAISS index and the researcher ID mapping from disk.

        Args:
            tag: Tag identifier for the index to load
            model: Model identifier for the index to load
            directory: Directory path containing index files

        Returns:
            True if successfully loaded, False if files not found

        Raises:
            Exception: If files exist but loading fails
        """
        key = (tag, model)

        directory = Path(directory)

        # Create safe filenames
        safe_tag = tag.replace("/", "_").replace(" ", "_")
        safe_model = model.replace("/", "_").replace(" ", "_")

        index_file = directory / f"index_{safe_tag}_{safe_model}.faiss"
        mapping_file = directory / f"mapping_{safe_tag}_{safe_model}.pkl"

        # Check if files exist
        if not index_file.exists() or not mapping_file.exists():
            logger.info(
                f"Index files not found for tag='{tag}', model='{model}' in {directory}"
            )
            return False

        # Load FAISS index
        index = faiss.read_index(str(index_file))

        # Load ID mapping
        with open(mapping_file, "rb") as f:
            id_mapping = pickle.load(f)

        # Store in memory
        self.indexes[key] = index
        self.id_mappings[key] = id_mapping
        self.loaded_at[key] = datetime.now()

        logger.info(
            f"Index loaded from disk: {index.ntotal} vectors for tag='{tag}', model='{model}'"
        )

        return True

    async def load_all_indexes(
        self, use_disk_cache: bool = True, cache_dir: Optional[str | Path] = None
    ) -> None:
        """
        Load all available indexes from database or disk cache.

        Queries the database for all unique (tag, model) combinations and loads
        their indexes. Optionally uses disk cache if available.

        Args:
            use_disk_cache: Whether to try loading from disk first (default: True)
            cache_dir: Directory for disk cache (default: "./faiss_indexes")
        """
        if cache_dir is None:
            cache_dir = Path("./faiss_indexes")
        else:
            cache_dir = Path(cache_dir)

        logger.info("Loading all embedding indexes...")

        # Query database for all unique (tag, model) combinations
        pipeline = [
            {"$group": {"_id": {"tag": "$tag", "model": "$model"}}},
            {"$project": {"_id": 0, "tag": "$_id.tag", "model": "$_id.model"}},
        ]

        combinations = await EmbeddingDocument.aggregate(pipeline).to_list()

        if not combinations:
            logger.warning("No embeddings found in database")
            return

        logger.info(f"Found {len(combinations)} embedding combinations to load")

        # Load each combination
        for combo in combinations:
            tag = combo["tag"]
            model = combo["model"]

            loaded_from_disk = False

            # Try loading from disk cache first
            if use_disk_cache:
                try:
                    loaded_from_disk = await self.load_index_from_disk(
                        tag, model, cache_dir
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to load index from disk for tag='{tag}', model='{model}': {e}"
                    )

            # If not loaded from disk, load from database
            if not loaded_from_disk:
                try:
                    await self.load_index(tag, model)

                    # Optionally save to disk for next time
                    if use_disk_cache:
                        try:
                            await self.save_index_to_disk(tag, model, cache_dir)
                        except Exception as e:
                            logger.warning(
                                f"Failed to save index to disk for tag='{tag}', model='{model}': {e}"
                            )
                except Exception as e:
                    logger.error(
                        f"Failed to load index for tag='{tag}', model='{model}': {e}"
                    )

        logger.info(f"Finished loading indexes: {len(self.indexes)} indexes loaded")

    def get_loaded_indexes(self) -> List[Tuple[str, str, int, datetime]]:
        """
        Get information about currently loaded indexes.

        Returns:
            List of (tag, model, num_vectors, loaded_at) tuples
        """
        result = []
        for (tag, model), index in self.indexes.items():
            num_vectors = index.ntotal
            loaded_at = self.loaded_at.get((tag, model), datetime.now())
            result.append((tag, model, num_vectors, loaded_at))

        return result

    def clear_index(self, tag: str, model: str) -> bool:
        """
        Remove an index from memory.

        Args:
            tag: Tag identifier for the index to clear
            model: Model identifier for the index to clear

        Returns:
            True if index was removed, False if it wasn't loaded
        """
        key = (tag, model)

        if key not in self.indexes:
            return False

        del self.indexes[key]
        del self.id_mappings[key]
        if key in self.loaded_at:
            del self.loaded_at[key]

        logger.info(f"Cleared index for tag='{tag}', model='{model}'")
        return True

    def clear_all_indexes(self) -> None:
        """Remove all indexes from memory."""
        self.indexes.clear()
        self.id_mappings.clear()
        self.loaded_at.clear()
        logger.info("All indexes cleared from memory")


# Global singleton instance
_embedding_index_manager: Optional[EmbeddingIndexManager] = None


def get_embedding_index_manager() -> EmbeddingIndexManager:
    """
    Get the global EmbeddingIndexManager singleton instance.

    Returns:
        The global EmbeddingIndexManager instance
    """
    global _embedding_index_manager

    if _embedding_index_manager is None:
        _embedding_index_manager = EmbeddingIndexManager()

    return _embedding_index_manager


async def get_all_embedding_tags_models() -> List[Tuple[str, str]]:
    """
    Query database for all unique (tag, model) combinations.

    This is useful for:
    - Loading all indexes at startup
    - Displaying available embedding versions
    - Validating user input

    Returns:
        List of (tag, model) tuples

    Example:
        >>> tags_models = await get_all_embedding_tags_models()
        >>> print(tags_models)
        [('v1_embeddings', 'gemini-embedding-001'),
         ('v2_embeddings', 'text-embedding-004')]
    """
    pipeline = [
        {"$group": {"_id": {"tag": "$tag", "model": "$model"}}},
        {"$project": {"_id": 0, "tag": "$_id.tag", "model": "$_id.model"}},
        {"$sort": {"tag": 1, "model": 1}},
    ]

    combinations = await EmbeddingDocument.aggregate(pipeline).to_list()

    return [(combo["tag"], combo["model"]) for combo in combinations]
