import faiss
import numpy as np
from typing import List, Dict, Tuple
from uuid import UUID


def build_faiss_index(
    embeddings: np.ndarray,
    use_gpu: bool = False,
    nlist: int = 100
) -> faiss.Index:
    dimension = embeddings.shape[1]
    n_samples = embeddings.shape[0]

    embeddings = embeddings.astype(np.float32)
    faiss.normalize_L2(embeddings)

    if n_samples < 1000:
        if use_gpu and faiss.get_num_gpus() > 0:
            res = faiss.StandardGpuResources()
            index = faiss.GpuIndexFlatIP(res, dimension)
        else:
            index = faiss.IndexFlatIP(dimension)
    else:
        quantizer = faiss.IndexFlatIP(dimension)
        index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_INNER_PRODUCT)

        index.train(embeddings)

        if use_gpu and faiss.get_num_gpus() > 0:
            res = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(res, 0, index)

    index.add(embeddings)

    return index


def search_similar_tracks(
    index: faiss.Index,
    query_embedding: np.ndarray,
    k: int = 20,
    nprobe: int = 10
) -> Tuple[np.ndarray, np.ndarray]:
    query_embedding = query_embedding.astype(np.float32)

    if query_embedding.ndim == 1:
        query_embedding = query_embedding.reshape(1, -1)

    faiss.normalize_L2(query_embedding)

    if hasattr(index, 'nprobe'):
        index.nprobe = nprobe

    distances, indices = index.search(query_embedding, k)

    return distances[0], indices[0]


def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-8)
    vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-8)

    similarity = np.dot(vec1_norm, vec2_norm)

    return float(similarity)


def batch_cosine_similarity(
    query: np.ndarray,
    candidates: np.ndarray
) -> np.ndarray:
    query_norm = query / (np.linalg.norm(query) + 1e-8)

    if candidates.ndim == 1:
        candidates = candidates.reshape(1, -1)

    candidate_norms = candidates / (np.linalg.norm(candidates, axis=1, keepdims=True) + 1e-8)

    similarities = np.dot(candidate_norms, query_norm)

    return similarities