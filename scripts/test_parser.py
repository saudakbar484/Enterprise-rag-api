import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.parser import chunk_text

sample_text = """
Retrieval-Augmented Generation (RAG) is a technique that enhances large language models
by combining them with external knowledge retrieval. Instead of relying solely on
information encoded during training, RAG systems retrieve relevant documents or passages
from a knowledge base at inference time, then use that retrieved content as context for
generating responses.

The RAG pipeline typically consists of two main components: a retriever and a generator.
The retriever is responsible for finding the most relevant documents given a user query,
while the generator uses those documents as context to produce accurate, grounded answers.

Enterprise RAG systems add additional complexity by supporting multiple tenants, each with
their own isolated document collections. This requires careful access control, efficient
vector indexing, and robust document processing pipelines. The document processing stage
involves parsing raw text, splitting it into manageable chunks, generating embeddings for
each chunk, and storing those embeddings in a vector database for fast retrieval.

Chunking strategy is critical in RAG systems. If chunks are too large, they may exceed
the context window of the language model. If they are too small, they may lack sufficient
context for the model to generate accurate answers. A common approach is to use fixed-size
chunks with a small overlap between successive chunks to prevent losing context at
boundaries. The overlap ensures that sentences or ideas that span chunk boundaries are
captured in at least one chunk completely.
""" * 3  # repeat to get enough tokens

chunks = chunk_text(sample_text)

print(f"Total chunks: {len(chunks)}")
print(f"{'─' * 60}")

for chunk in chunks:
    print(f"Chunk {chunk.index:02d} | tokens: {chunk.token_count:>3} | range: [{chunk.start_token} - {chunk.end_token}]")

print(f"{'─' * 60}")
print(f"\nChunk 0 preview:\n{chunks[0].text[:200]}...")
if len(chunks) > 1:
    print(f"\nChunk 1 preview (should overlap with Chunk 0):\n{chunks[1].text[:200]}...")