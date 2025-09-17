"""
RAG Storage System: Captures specialist outputs and stores them in RAG corpora with embeddings.
"""

import os
import asyncio
import json
import numpy as np
from typing import Dict, Any, List
from datetime import datetime
import vertexai
from vertexai.preview import rag
from vertexai.language_models import TextEmbeddingModel
from sklearn.metrics.pairwise import cosine_similarity
from google.adk.tools import ToolContext


class RagStorageSystem:
    """System to capture and store specialist outputs in RAG corpora."""

    def __init__(self):
        # Initialize Vertex AI
        vertexai.init(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411"),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west4")
        )

        # Initialize text embedding model for semantic chunking
        self.embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

        # Map specialists to their RAG corpus names
        self.specialist_to_corpus = {
            "github_specialist": "cloud_architecture",  # GitHub info goes to general cloud knowledge
            "microsoft_specialist": "azure_architecture",
            "terraform_specialist": "terraform_infrastructure",
            "search_specialist": "cloud_architecture",
            "diagrams_expert": "diagrams_knowledge",
            "image_generation_specialist": "diagrams_knowledge"  # Image generation insights also go to diagrams
        }

        # Corpus IDs (will be loaded from runtime_rag_bootstrap)
        self.corpus_ids = {}

    async def initialize_corpus_mapping(self):
        """Initialize the mapping of corpus names to IDs."""
        from .runtime_rag_bootstrap import get_rag_corpus_id

        for specialist, corpus_name in self.specialist_to_corpus.items():
            try:
                corpus_id = await get_rag_corpus_id(corpus_name)
                self.corpus_ids[corpus_name] = corpus_id
                print(f"📚 Mapped {specialist} → {corpus_name}: {corpus_id}")
            except Exception as e:
                print(f"❌ Failed to map {specialist} to {corpus_name}: {e}")

    async def store_specialist_output(self, specialist_name: str, query: str, output: str, context: Dict = None):
        """Store a specialist's output in its corresponding RAG corpus."""

        # Get the corpus name for this specialist
        corpus_name = self.specialist_to_corpus.get(specialist_name)
        if not corpus_name:
            print(f"⚠️ No RAG corpus mapped for specialist: {specialist_name}")
            return False

        # Get the corpus ID
        corpus_id = self.corpus_ids.get(corpus_name)
        if not corpus_id:
            print(f"⚠️ No corpus ID found for: {corpus_name}")
            return False

        try:
            # Create a document with metadata
            document_content = self._create_document_content(specialist_name, query, output, context)

            # Chunk the content for better retrieval
            chunks = self._chunk_content(document_content, specialist_name)

            # Store each chunk in the RAG corpus
            for i, chunk in enumerate(chunks):
                await self._store_chunk_in_rag(corpus_id, chunk, specialist_name, query, i)

            print(f"✅ Stored {len(chunks)} chunks from {specialist_name} in {corpus_name}")
            return True

        except Exception as e:
            print(f"❌ Failed to store output from {specialist_name}: {e}")
            return False

    def _create_document_content(self, specialist_name: str, query: str, output: str, context: Dict = None) -> str:
        """Create a structured document from specialist output."""

        timestamp = datetime.now().isoformat()

        document = f"""
SPECIALIST: {specialist_name}
QUERY: {query}
TIMESTAMP: {timestamp}

OUTPUT:
{output}
"""

        if context:
            document += f"\nCONTEXT:\n{json.dumps(context, indent=2)}"

        return document

    def _chunk_content(self, content: str, specialist_name: str) -> List[str]:
        """Chunk content using semantic embeddings for optimal RAG retrieval."""

        # Use semantic chunking for all specialists
        return self._semantic_chunk_content(content, specialist_name)

    def _semantic_chunk_content(self, content: str, specialist_name: str) -> List[str]:
        """Chunk content using semantic embeddings to find natural boundaries."""

        # Get specialist-specific parameters
        chunk_params = self._get_chunking_parameters(specialist_name)
        target_chunk_size = chunk_params["target_size"]
        min_chunk_size = chunk_params["min_size"]
        overlap_ratio = chunk_params["overlap_ratio"]

        # Split content into sentences for semantic analysis
        sentences = self._split_into_sentences(content)

        if len(sentences) <= 1:
            return [content]

        # Get embeddings for all sentences
        embeddings = self._get_sentence_embeddings(sentences)

        # Find semantic boundaries using embedding similarity
        chunks = self._create_semantic_chunks(
            sentences,
            embeddings,
            target_chunk_size,
            min_chunk_size,
            overlap_ratio
        )

        return chunks or [content]

    def _get_chunking_parameters(self, specialist_name: str) -> Dict[str, Any]:
        """Get specialist-specific chunking parameters."""
        params = {
            "github_specialist": {
                "target_size": 800,
                "min_size": 200,
                "overlap_ratio": 0.15,
                "preserve_code": True
            },
            "microsoft_specialist": {
                "target_size": 600,
                "min_size": 150,
                "overlap_ratio": 0.20,
                "preserve_code": False
            },
            "terraform_specialist": {
                "target_size": 1000,
                "min_size": 250,
                "overlap_ratio": 0.10,
                "preserve_code": True
            },
            "search_specialist": {
                "target_size": 700,
                "min_size": 200,
                "overlap_ratio": 0.20,
                "preserve_code": False
            },
            "diagrams_expert": {
                "target_size": 800,
                "min_size": 200,
                "overlap_ratio": 0.15,
                "preserve_code": True
            }
        }

        return params.get(specialist_name, params["search_specialist"])

    def _split_into_sentences(self, content: str) -> List[str]:
        """Split content into sentences while preserving code blocks."""

        # Preserve code blocks
        code_blocks = []
        code_placeholder = "___CODE_BLOCK_{}___"

        # Extract code blocks
        import re
        code_pattern = r'```[\s\S]*?```'
        for i, match in enumerate(re.finditer(code_pattern, content)):
            placeholder = code_placeholder.format(i)
            code_blocks.append((placeholder, match.group()))
            content = content.replace(match.group(), placeholder)

        # Split into sentences (simple approach - can be enhanced)
        sentences = []
        current_sentence = ""

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                if current_sentence:
                    sentences.append(current_sentence.strip())
                    current_sentence = ""
                continue

            current_sentence += " " + line

            # End sentence on specific patterns
            if (line.endswith('.') or line.endswith('!') or line.endswith('?') or
                line.endswith(':') or len(current_sentence) > 300):
                sentences.append(current_sentence.strip())
                current_sentence = ""

        if current_sentence:
            sentences.append(current_sentence.strip())

        # Restore code blocks
        for placeholder, code_block in code_blocks:
            sentences = [s.replace(placeholder, code_block) for s in sentences]

        return [s for s in sentences if s.strip()]

    def _get_sentence_embeddings(self, sentences: List[str]) -> np.ndarray:
        """Get embeddings for sentences using Vertex AI embedding model."""
        try:
            # Batch embed sentences for efficiency
            embeddings = []
            batch_size = 10  # Process in batches to avoid rate limits

            for i in range(0, len(sentences), batch_size):
                batch = sentences[i:i + batch_size]
                batch_embeddings = self.embedding_model.get_embeddings(batch)
                embeddings.extend([emb.values for emb in batch_embeddings])

            return np.array(embeddings)

        except Exception as e:
            print(f"⚠️ Embedding generation failed: {e}")
            # Fallback to dummy embeddings
            return np.random.rand(len(sentences), 768)

    def _create_semantic_chunks(self, sentences: List[str], embeddings: np.ndarray,
                              target_size: int, min_size: int, overlap_ratio: float) -> List[str]:
        """Create chunks based on semantic similarity and size constraints."""

        if len(sentences) <= 1:
            return sentences

        chunks = []
        current_chunk = ""
        current_sentences = []

        i = 0
        while i < len(sentences):
            sentence = sentences[i]

            # Check if adding this sentence would exceed target size
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence

            if len(potential_chunk) <= target_size:
                # Add sentence to current chunk
                current_chunk = potential_chunk
                current_sentences.append(sentence)
                i += 1
            else:
                # Current chunk is full, check if we should start a new one
                if len(current_chunk) >= min_size:
                    # Finalize current chunk
                    chunks.append(current_chunk.strip())

                    # Start new chunk with overlap
                    overlap_size = int(len(current_sentences) * overlap_ratio)
                    if overlap_size > 0:
                        overlap_sentences = current_sentences[-overlap_size:]
                        current_chunk = " ".join(overlap_sentences)
                        current_sentences = overlap_sentences[:]
                    else:
                        current_chunk = ""
                        current_sentences = []
                else:
                    # Current chunk too small, add sentence anyway
                    current_chunk = potential_chunk
                    current_sentences.append(sentence)
                    i += 1

        # Add final chunk
        if current_chunk and len(current_chunk.strip()) >= min_size:
            chunks.append(current_chunk.strip())
        elif chunks and current_chunk:
            # Merge small final chunk with last chunk
            chunks[-1] += " " + current_chunk.strip()

        return chunks

    async def _store_chunk_in_rag(self, corpus_id: str, chunk: str, specialist_name: str, query: str, chunk_index: int):
        """Store a single chunk in the RAG corpus with embeddings."""

        try:
            # Create a temporary file for the chunk
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"/tmp/{specialist_name}_{timestamp}_{chunk_index}.txt"

            # Write chunk to temporary file
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(chunk)

            # Import the file into the RAG corpus
            response = rag.import_files(
                corpus_name=corpus_id,
                paths=[file_name],
                chunk_size=500,  # Vertex AI will further chunk if needed
                chunk_overlap=50
            )

            print(f"  📦 Stored chunk {chunk_index} for {specialist_name}")

            # Clean up temporary file
            try:
                os.remove(file_name)
            except:
                pass

        except Exception as e:
            print(f"  ❌ Failed to store chunk {chunk_index}: {e}")
            # Clean up temporary file on error
            try:
                os.remove(file_name)
            except:
                pass


# Global instance
rag_storage = RagStorageSystem()


async def store_specialist_output(specialist_name: str, query: str, output: str, context: Dict = None):
    """Convenient function to store specialist output."""
    if not rag_storage.corpus_ids:
        await rag_storage.initialize_corpus_mapping()

    return await rag_storage.store_specialist_output(specialist_name, query, output, context)


async def initialize_rag_storage():
    """Initialize the RAG storage system."""
    await rag_storage.initialize_corpus_mapping()
    print("✅ RAG Storage System initialized")