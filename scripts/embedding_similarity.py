import numpy as np
from sentence_transformers import SentenceTransformer

# ── Load model ──
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# ── Sentences to embed ──
sentences = [
    "Enterprise software helps businesses manage operations efficiently.",
    "Companies use software platforms to streamline their workflows.",
    "The weather in Islamabad is warm during summer months.",
]

# ── Generate embeddings ──
print("\nGenerating embeddings...")
embeddings = model.encode(sentences)

print(f"Embedding shape: {embeddings.shape}")  # (3, 384)

# ── Cosine similarity function ──
def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    return dot_product / (norm_a * norm_b)

# ── Calculate similarities ──
print("\n── Cosine Similarity Results ──")

pairs = [
    (0, 1, "Sentence 1 vs Sentence 2 (similar topic)"),
    (0, 2, "Sentence 1 vs Sentence 3 (different topic)"),
    (1, 2, "Sentence 2 vs Sentence 3 (different topic)"),
]

for i, j, label in pairs:
    score = cosine_similarity(embeddings[i], embeddings[j])
    print(f"\n{label}")
    print(f"  Score: {score:.4f}")
    print(f"  Interpretation: {'Similar ✓' if score > 0.5 else 'Dissimilar ✗'}")

# ── Print sentence recap ──
print("\n── Sentences ──")
for idx, s in enumerate(sentences, 1):
    print(f"  {idx}. {s}")