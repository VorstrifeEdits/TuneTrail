import numpy as np
from typing import List, Set


def compute_recall_at_k(
    recommended: List,
    relevant: Set,
    k: int = 20
) -> float:
    if not relevant:
        return 0.0

    top_k = set(recommended[:k])

    hits = len(top_k & relevant)

    recall = hits / len(relevant)

    return recall


def compute_ndcg(
    recommended: List,
    relevant: Set,
    k: int = 20
) -> float:
    top_k = recommended[:k]

    dcg = 0.0
    for i, item in enumerate(top_k):
        if item in relevant:
            dcg += 1.0 / np.log2(i + 2)

    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))

    if idcg == 0:
        return 0.0

    ndcg = dcg / idcg

    return ndcg


def compute_mrr(
    recommended: List,
    relevant: Set
) -> float:
    for i, item in enumerate(recommended):
        if item in relevant:
            return 1.0 / (i + 1)

    return 0.0


def compute_precision_at_k(
    recommended: List,
    relevant: Set,
    k: int = 20
) -> float:
    top_k = set(recommended[:k])

    hits = len(top_k & relevant)

    precision = hits / k if k > 0 else 0.0

    return precision


def compute_f1_score(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0

    f1 = 2 * (precision * recall) / (precision + recall)

    return f1


def compute_map(
    all_recommendations: List[List],
    all_relevant: List[Set]
) -> float:
    aps = []

    for recommended, relevant in zip(all_recommendations, all_relevant):
        if not relevant:
            continue

        precisions = []
        hits = 0

        for k, item in enumerate(recommended, 1):
            if item in relevant:
                hits += 1
                precisions.append(hits / k)

        if precisions:
            aps.append(np.mean(precisions))

    if not aps:
        return 0.0

    return np.mean(aps)