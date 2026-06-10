import time
import uuid
import random

import numpy as np
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

from app.core.vector_store import client, COLLECTION_NAME, VECTOR_SIZE

NUM_TENANTS = 5
ROWS_PER_TENANT = 2000  # 5 * 2000 = 10,000
BATCH_SIZE = 200
LATENCY_THRESHOLD_MS = 50

TENANT_IDS = [f"tenant-{i}" for i in range(NUM_TENANTS)]

def generate_points() -> list[PointStruct]:
    points = []
    for tenant_id in TENANT_IDS:
        for i in range(ROWS_PER_TENANT):
            vector = np.random.rand(VECTOR_SIZE).tolist()
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "tenant_id": tenant_id,
                        "text": f"synthetic document {i} for {tenant_id}",
                    },
                )
            )
    return points

def populate_collection(points: list[PointStruct]):
    print(f"Upserting {len(points)} points in batches of {BATCH_SIZE}...")
    for start in range(0, len(points), BATCH_SIZE):
        batch = points[start:start + BATCH_SIZE]
        client.upsert(collection_name=COLLECTION_NAME, points=batch, wait=False)
    print("Upload complete.")

def wait_for_indexing(timeout_s: int = 60):
    print("Waiting for Qdrant to finish indexing...")
    start = time.time()
    while time.time() - start < timeout_s:
        info = client.get_collection(COLLECTION_NAME)
        if info.status == "green" and info.indexed_vectors_count >= info.points_count:
            print(f"Indexing complete. indexed={info.indexed_vectors_count}, points={info.points_count}")
            return
        time.sleep(1)
    print("Warning: indexing did not fully complete within timeout.")

def warmup(num_queries: int = 10):
    print("Running warm-up queries...")
    for _ in range(num_queries):
        query_vector = np.random.rand(VECTOR_SIZE).tolist()
        client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=5,
        )

def benchmark_and_verify_isolation(num_queries_per_tenant: int = 20):
    failures = []
    latencies = []

    for tenant_id in TENANT_IDS:
        for _ in range(num_queries_per_tenant):
            query_vector = np.random.rand(VECTOR_SIZE).tolist()

            start = time.perf_counter()
            results = client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                query_filter=Filter(
                    must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
                ),
                limit=5,
            ).points
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

            if elapsed_ms > LATENCY_THRESHOLD_MS:
                failures.append(f"Latency {elapsed_ms:.2f}ms exceeded {LATENCY_THRESHOLD_MS}ms for {tenant_id}")

            for point in results:
                if point.payload.get("tenant_id") != tenant_id:
                    failures.append(
                        f"LEAK: query for {tenant_id} returned point from {point.payload.get('tenant_id')}"
                    )

    return latencies, failures

if __name__ == "__main__":
    points = generate_points()
    populate_collection(points)

    wait_for_indexing()
    warmup()

    latencies, failures = benchmark_and_verify_isolation()

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)

    print(f"\nQueries run: {len(latencies)}")
    print(f"Avg latency: {avg_latency:.2f}ms")
    print(f"Max latency: {max_latency:.2f}ms")

    if failures:
        print(f"\n{len(failures)} FAILURES:")
        for f in failures[:10]:
            print(f"  - {f}")
        raise SystemExit(1)

    print("\nAll checks passed: latency under threshold, no cross-tenant leakage.")