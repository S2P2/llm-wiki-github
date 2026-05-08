# Understanding Vector Databases

Vector databases are specialized database systems designed to store and query
high-dimensional vectors. They power semantic search, recommendation systems,
and retrieval-augmented generation (RAG) pipelines.

## How Vector Embeddings Work

Text and other data are converted into numerical vectors using embedding models
like OpenAI's text-embedding-3-small or open-source alternatives like BGE. Each
vector captures semantic meaning in a high-dimensional space (typically 384 to
3072 dimensions).

## Approximate Nearest Neighbor Search

Vector databases use approximate nearest neighbor (ANN) algorithms to quickly
find similar vectors without comparing against every entry. Popular ANN
approaches include:

- **HNSW (Hierarchical Navigable Small World):** Used by Milvus, Weaviate, and
  Qdrant. Provides excellent recall with moderate memory usage.
- **IVF (Inverted File Index):** Partitions vectors into clusters, reducing
  search scope. Used in FAISS.
- **Product Quantization:** Compresses vectors for memory-efficient storage at
  the cost of some accuracy.

## Popular Vector Database Systems

- **Milvus:** Open-source, supports multiple index types, designed for
  billion-scale datasets.
- **Qdrant:** Rust-based, offers filtering with vector search, lightweight
  deployment.
- **Weaviate:** Includes built-in modules for vectorization and generative
  search.
- **ChromaDB:** Lightweight, designed for AI application development.
- **Pinecone:** Fully managed service with automatic scaling.

## When to Use Vector Search vs. Traditional Search

Vector search excels at semantic similarity — finding content that *means*
similar things even without matching keywords. Traditional keyword search
(BM25, TF-IDF) remains better for exact term matching. Many production systems
use hybrid approaches combining both methods.

## Integration with LLMs

Vector databases serve as the retrieval backbone in RAG architectures. The
workflow: user query → embedding → vector search → top-k results → injected
into LLM context → generated response. This grounds LLM outputs in specific,
retrieved knowledge rather than relying solely on training data.
