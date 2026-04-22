"""
RAG (Retrieval Augmented Generation) system with vector DB for storing and retrieving
AppDynamics documentation and best practices.
"""

import json
import os
import re
from typing import List, Dict, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False


class VectorDB:
    """
    Simple vector database for storing and retrieving documents with embeddings.
    """
    
    def __init__(self, kb_dir: str = "./kb_data", model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize Vector DB.
        
        Args:
            kb_dir: Directory to store documents and embeddings
            model_name: Sentence-transformers model name
        """
        self.kb_dir = kb_dir
        self.model_name = model_name
        self.model = None
        self.documents = {}  # {doc_id: {"content": str, "category": str, "embedding": array}}
        self.embeddings = {}  # {doc_id: embedding_vector}
        use_embeddings = os.getenv("RAG_USE_EMBEDDINGS", "0").strip().lower() in {"1", "true", "yes"}
        
        if HAS_EMBEDDINGS and use_embeddings:
            self._initialize_model()
        
        self._ensure_kb_dir()
        self._load_documents()
    
    def _initialize_model(self):
        """Initialize the embedding model."""
        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            print(f"Warning: Could not load embedding model: {e}")
            self.model = None
    
    def _ensure_kb_dir(self):
        """Create KB directory if it doesn't exist."""
        if not os.path.exists(self.kb_dir):
            os.makedirs(self.kb_dir, exist_ok=True)
    
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for text."""
        if self.model is None:
            return None
        try:
            return self.model.encode(text, convert_to_numpy=True)
        except Exception as e:
            print(f"Warning: Could not encode text: {e}")
            return None

    def _retrieve_by_keywords(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[Dict]:
        """Fallback retrieval when embeddings are unavailable."""
        query_tokens = set(re.findall(r"[a-z0-9_.-]+", (query or "").lower()))
        if not query_tokens:
            return []

        results = []
        for doc_id, doc in self.documents.items():
            if category and doc.get("category") != category:
                continue

            content = (doc.get("content") or "").lower()
            if not content:
                continue

            score = 0.0
            for token in query_tokens:
                if token in content:
                    score += 1.0

            if score <= 0:
                continue

            # Normalize by query size to keep score in [0, 1].
            norm_score = score / max(len(query_tokens), 1)
            results.append(
                {
                    "doc_id": doc_id,
                    "content": doc.get("content", ""),
                    "category": doc.get("category", "general"),
                    "score": float(norm_score),
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def add_document(self, doc_id: str, content: str, category: str = "general") -> bool:
        """
        Add a document to the vector DB.
        
        Args:
            doc_id: Unique document identifier
            content: Document content
            category: Document category (e.g., "error-resolution", "bct-guide", "controller-config")
        
        Returns:
            True if successful
        """
        try:
            embedding = self._get_embedding(content)
            self.documents[doc_id] = {
                "content": content,
                "category": category,
                "embedding": embedding.tolist() if embedding is not None else None
            }
            if embedding is not None:
                self.embeddings[doc_id] = embedding
            self._save_documents()
            return True
        except Exception as e:
            print(f"Error adding document: {e}")
            return False
    
    def retrieve(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[Dict]:
        """
        Retrieve top-k relevant documents.
        
        Args:
            query: Query text
            top_k: Number of top documents to retrieve
            category: Filter by category (optional)
        
        Returns:
            List of retrieved documents with relevance scores
        """
        if not self.documents:
            return []
        
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return self._retrieve_by_keywords(query, top_k=top_k, category=category)
        
        # Calculate similarity scores
        results = []
        for doc_id, embedding in self.embeddings.items():
            if embedding is None:
                continue
            
            doc = self.documents[doc_id]
            if category and doc.get("category") != category:
                continue
            
            # Cosine similarity
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding) + 1e-8
            )
            results.append({
                "doc_id": doc_id,
                "content": doc["content"],
                "category": doc["category"],
                "score": float(similarity)
            })
        
        # Sort by relevance and return top-k
        results.sort(key=lambda x: x["score"], reverse=True)
        top_results = results[:top_k]
        if top_results:
            return top_results

        # If embedding-based retrieval produced no results, fall back to keywords.
        return self._retrieve_by_keywords(query, top_k=top_k, category=category)
    
    def _save_documents(self):
        """Save documents to disk."""
        try:
            data = {
                doc_id: {
                    "content": doc["content"],
                    "category": doc["category"],
                    "embedding": doc.get("embedding")
                }
                for doc_id, doc in self.documents.items()
            }
            with open(os.path.join(self.kb_dir, "documents.json"), "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving documents: {e}")
    
    def _load_documents(self):
        """Load documents from disk."""
        try:
            doc_file = os.path.join(self.kb_dir, "documents.json")
            if os.path.exists(doc_file):
                with open(doc_file, "r") as f:
                    data = json.load(f)
                    for doc_id, doc_data in data.items():
                        self.documents[doc_id] = {
                            "content": doc_data["content"],
                            "category": doc_data["category"],
                            "embedding": doc_data.get("embedding")
                        }
                        if doc_data.get("embedding") and self.model:
                            self.embeddings[doc_id] = np.array(doc_data["embedding"])
        except Exception as e:
            print(f"Warning: Could not load documents: {e}")


# Global DB instance
_db_instance = None


def get_vector_db(kb_dir: str = "./kb_data") -> VectorDB:
    """Get or create the global vector DB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = VectorDB(kb_dir)
    return _db_instance


def format_retrieved_docs(retrieved_docs: List[Dict]) -> str:
    """Format retrieved documents for inclusion in the prompt."""
    if not retrieved_docs:
        return "No relevant documentation found in knowledge base."
    
    context = "=== RETRIEVED APPLDYNAMICS DOCUMENTATION ===\n\n"
    for i, doc in enumerate(retrieved_docs, 1):
        context += f"[{i}] ({doc['category']}, Relevance: {doc['score']:.2f})\n"
        context += f"{doc['content']}\n\n"
    return context

