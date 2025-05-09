# api/metrics.py

import math
from flask import Blueprint, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

metrics_bp = Blueprint("metrics", __name__)

@metrics_bp.route("/metrics")
def metrics():
    """
    Exponiere die Prometheus-Metriken.
    """
    data = generate_latest()
    return Response(data, mimetype=CONTENT_TYPE_LATEST)


def compute_ndcg(predictions: list, ground_truth: list) -> float:
    """
    Normalized Discounted Cumulative Gain (binäre Relevanz).
    :param predictions: Liste von Artikel-Links/IDs in vorhergesagter Reihenfolge
    :param ground_truth: Liste der tatsächlich relevanten Links/IDs
    :return: NDCG-Wert in [0,1]
    """
    # binäre Relevanz: 1 wenn in ground_truth, sonst 0
    rels = [1 if doc in ground_truth else 0 for doc in predictions]
    # DCG
    dcg = sum((2**rel - 1) / math.log2(idx + 2) for idx, rel in enumerate(rels))
    # ideal DCG (alle relevanten am Anfang)
    ideal_k = min(len(ground_truth), len(predictions))
    idcg = sum((2**1 - 1) / math.log2(i + 2) for i in range(ideal_k))
    return (dcg / idcg) if idcg > 0 else 0.0


def compute_map(predictions: list, ground_truth: list) -> float:
    """
    Mean Average Precision (MAP) für eine einzelne Query.
    :param predictions: Liste von Artikel-Links/IDs in vorhergesagter Reihenfolge
    :param ground_truth: Liste der tatsächlich relevanten Links/IDs
    :return: MAP-Wert in [0,1]
    """
    num_relevant = 0
    sum_prec = 0.0
    for idx, doc in enumerate(predictions, start=1):
        if doc in ground_truth:
            num_relevant += 1
            sum_prec += num_relevant / idx
    return (sum_prec / num_relevant) if num_relevant > 0 else 0.0
