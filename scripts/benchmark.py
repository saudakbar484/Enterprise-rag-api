import time
import random
import uuid
import statistics
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

# ── Config ──
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "tenant_documents"
TOTAL_POINTS = 10000
NUM_TENANTS = 5
BATCH_SIZE = 500
RETRIEVAL_LIMIT = 15
TARGET_MS = 50  # sub-50ms assertion

# ── Setup ──
client = QdrantClient(url=QDRANT_URL)
model = SentenceTransformer("all-MiniLM-L6-v2")

# ── Generate 5 fixed tenant IDs ──
TENANT_IDS = [str(uuid.uuid4()) for _ in range(NUM_TENANTS)]

# ── Synthetic text templates ──
TEMPLATES = [
    "The company {name} reported revenue of ${amount}M in Q{q} {year}.",
    "Patient {id} was diagnosed with {condition} and prescribed {drug}.",
    "Employee {name} joined the {dept} department on {date}.",
    "Order #{id} for {product} was shipped to {city} on {date}.",
    "Document {id} contains policy details for {topic} compliance.",
    "The project {name} achieved {pct}% completion in {month} {year}.",
    "Tenant {id} uploaded {count} files related to {topic} processing.",
    "The system logged {count} errors in module {module} at {time}.",
    "Invoice #{id} for ${amount} was issued to client {name}.",
    "Research paper on {topic} was published in {journal} in {year}.",
]

WORDS = ["Alpha", "Beta", "Gamma", "Delta", "Sigma", "Omega",
         "neural", "quantum", "enterprise", "pipeline", "vector",
         "retrieval", "embedding", "transformer", "inference"]


def random_text() -> str:
    template = random.choice(TEMPLATES)
    return template.format(
        name=random.choice(WORDS),
        amount=random.randint(10, 999),
        q=random.randint(1, 4),
        year=random.randint(2020, 2025),
        id=random.randint(1000, 9999),
        condition=random.choice(WORDS),
        drug=random.choice(WORDS),
        dept=random.choice(WORDS),
        date=f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        product=random.choice(WORDS),
        city=random.choice(WORDS),
        topic=random.choice(WORDS),
        pct=random.randint(10, 100),
        month=random.choice(["Jan","Feb","Mar","Apr","May","Jun"]),
        count=random.randint(1, 500),
        module=random.choice(WORDS),
        time=f"{random.randint(0,23):02d}:{random.randint(0,59):02d}",
        journal=random.choice(WORDS),
    )


def populate_database():
    print(f"\n{'='*60}")
    print(f"POPULATING DATABASE")
    print(f"  Total points : {TOTAL_POINTS}")
    print(f"  Tenants      : {NUM_TENANTS}")
    print(f"  Batch size   : {BATCH_SIZE}")
    print(f"{'='*60}")

    points_per_tenant = TOTAL_POINTS // NUM_TENANTS
    total_inserted = 0

    for t_idx, tenant_id in enumerate(TENANT_IDS):
        print(f"\nTenant {t_idx+1}/{NUM_TENANTS}: {tenant_id[:8]}...")
        tenant_points = []

        for i in range(0, points_per_tenant, BATCH_SIZE):
            batch_texts = [random_text() for _ in range(BATCH_SIZE)]
            embeddings = model.encode(batch_texts, show_progress_bar=False)

            batch_points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embeddings[j].tolist(),
                    payload={
                        "tenant_id": tenant_id,
                        "text": batch_texts[j],
                        "chunk_index": i + j,
                        "doc_filename": f"synthetic_{t_idx}.txt",
                    },
                )
                for j in range(len(batch_texts))
            ]
            tenant_points.extend(batch_points)
            total_inserted += len(batch_points)
            print(f"  Inserted batch {i//BATCH_SIZE + 1} — total: {total_inserted}")

        client.upsert(collection_name=COLLECTION_NAME, points=tenant_points)

    print(f"\n✓ Population complete — {total_inserted} points inserted")


def run_retrieval_benchmark():
    print(f"\n{'='*60}")
    print(f"RETRIEVAL BENCHMARK")
    print(f"  Queries per tenant : 10")
    print(f"  Target latency     : <{TARGET_MS}ms")
    print(f"{'='*60}")

    query_texts = [
        "company revenue quarterly financial report",
        "employee department joining date",
        "order shipment product delivery",
        "system error module logging",
        "research paper published journal",
        "project completion percentage milestone",
        "invoice client payment amount",
        "patient diagnosis prescription medical",
        "document policy compliance details",
        "pipeline processing vector embedding",
    ]

    all_latencies = []
    failures = []

    for t_idx, tenant_id in enumerate(TENANT_IDS):
        tenant_latencies = []
        print(f"\nTenant {t_idx+1}: {tenant_id[:8]}...")

        for query in query_texts:
            query_vector = model.encode([query])[0].tolist()

            tenant_filter = Filter(
                must=[FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id)
                )]
            )

            start = time.perf_counter()
            response = client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                query_filter=tenant_filter,
                limit=RETRIEVAL_LIMIT,
                with_payload=True,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            tenant_latencies.append(elapsed_ms)
            all_latencies.append(elapsed_ms)

            # Assert sub-50ms
            status = "✓" if elapsed_ms < TARGET_MS else "✗ SLOW"
            if elapsed_ms >= TARGET_MS:
                failures.append((tenant_id[:8], query[:30], elapsed_ms))

            print(f"  [{status}] {elapsed_ms:.2f}ms — {query[:40]}")

        avg = statistics.mean(tenant_latencies)
        print(f"  Avg: {avg:.2f}ms")

    return all_latencies, failures


def run_isolation_test():
    print(f"\n{'='*60}")
    print(f"TENANT ISOLATION TEST")
    print(f"{'='*60}")

    query_text = "company revenue financial report"
    query_vector = model.encode([query_text])[0].tolist()
    passed = True

    for t_idx, tenant_id in enumerate(TENANT_IDS):
        tenant_filter = Filter(
            must=[FieldCondition(
                key="tenant_id",
                match=MatchValue(value=tenant_id)
            )]
        )

        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=tenant_filter,
            limit=RETRIEVAL_LIMIT,
            with_payload=True,
        )

        for point in response.points:
            returned_tenant = point.payload.get("tenant_id")
            if returned_tenant != tenant_id:
                print(f"  ✗ LEAK DETECTED: Tenant {tenant_id[:8]} got data from {returned_tenant[:8]}")
                passed = False
            else:
                pass

        print(f"  ✓ Tenant {t_idx+1} ({tenant_id[:8]}): {len(response.points)} results — no leaks")

    return passed


def print_summary(all_latencies, failures, isolation_passed):
    print(f"\n{'='*60}")
    print(f"BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"  Total queries    : {len(all_latencies)}")
    print(f"  Min latency      : {min(all_latencies):.2f}ms")
    print(f"  Max latency      : {max(all_latencies):.2f}ms")
    print(f"  Avg latency      : {statistics.mean(all_latencies):.2f}ms")
    print(f"  P95 latency      : {sorted(all_latencies)[int(len(all_latencies)*0.95)]:.2f}ms")
    print(f"  Sub-{TARGET_MS}ms queries : {len([l for l in all_latencies if l < TARGET_MS])}/{len(all_latencies)}")
    print(f"  Slow queries     : {len(failures)}")
    print(f"  Isolation        : {'✓ PASSED' if isolation_passed else '✗ FAILED'}")

    if failures:
        print(f"\n  Slow query details:")
        for tenant, query, ms in failures:
            print(f"    Tenant {tenant}: '{query}' — {ms:.2f}ms")

    overall = len(failures) == 0 and isolation_passed
    print(f"\n  Overall result   : {'✓ ALL ASSERTIONS PASSED' if overall else '✗ SOME ASSERTIONS FAILED'}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
     # populate_database()
     # Warmup — discard first query latency
    print("\nWarming up...")
    warmup_vector = model.encode(["warmup query"])[0].tolist()
    client.query_points(
        collection_name=COLLECTION_NAME,
        query=warmup_vector,
        limit=1,
        with_payload=False,
    )
    print("Warmup complete.\n")

    all_latencies, failures = run_retrieval_benchmark()
    isolation_passed = run_isolation_test()
    print_summary(all_latencies, failures, isolation_passed)