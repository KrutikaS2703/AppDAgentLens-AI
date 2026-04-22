"""
Initialize knowledge base with AppDynamics documentation from kb_documents/ folder.
Each .txt file in kb_documents/ is automatically loaded as a KB document.

File format:
- Metadata at top (lines starting with #)
- # category: <category_name>
- # tags: <comma-separated tags>
- Content follows after blank line

Example:
# category: controller-config
# tags: ssl, connection, timeout

Content here...
"""

import os
from ai.rag import get_vector_db


def parse_kb_file(file_path: str) -> dict:
    """
    Parse a KB document file.
    
    Extracts metadata from comments at the top and returns document info.
    """
    doc_id = os.path.splitext(os.path.basename(file_path))[0]
    category = "general"
    tags = []
    content_lines = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read metadata
            parsing_metadata = True
            for line in f:
                if parsing_metadata:
                    if line.startswith("# category:"):
                        category = line.replace("# category:", "").strip()
                    elif line.startswith("# tags:"):
                        tags_str = line.replace("# tags:", "").strip()
                        tags = [tag.strip() for tag in tags_str.split(",")]
                    elif line.startswith("#"):
                        # Other metadata lines, skip
                        continue
                    elif line.strip() == "":
                        # Blank line marks end of metadata
                        parsing_metadata = False
                    else:
                        # Non-comment line, start of content
                        parsing_metadata = False
                        content_lines.append(line)
                else:
                    content_lines.append(line)
        
        content = "".join(content_lines).strip()
        
        return {
            "doc_id": doc_id,
            "content": content,
            "category": category,
            "tags": tags
        }
    except Exception as e:
        print(f"Error parsing KB file {file_path}: {e}")
        return None


def load_kb_documents() -> list:
    """
    Load all KB documents from kb_documents/ folder.
    
    Returns:
        List of document dicts
    """
    kb_dir = os.path.join(os.path.dirname(__file__), "..", "kb_documents")
    
    if not os.path.exists(kb_dir):
        print(f"Warning: KB documents folder not found: {kb_dir}")
        return []
    
    documents = []
    for filename in os.listdir(kb_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(kb_dir, filename)
            doc = parse_kb_file(file_path)
            if doc:
                documents.append(doc)
    
    return documents





def initialize_kb():
    """
    Initialize the vector database with AppDynamics documentation from kb_documents/ folder.
    Re-indexes automatically when the set of files in kb_documents/ changes.
    """
    db = get_vector_db()

    # Determine current file set in kb_documents
    kb_dir = os.path.join(os.path.dirname(__file__), "..", "kb_documents")
    current_doc_ids = set()
    if os.path.exists(kb_dir):
        current_doc_ids = {
            os.path.splitext(f)[0]
            for f in os.listdir(kb_dir)
            if f.endswith(".txt")
        }

    # Skip re-indexing only when the indexed set exactly matches the file set
    if current_doc_ids and set(db.documents.keys()) == current_doc_ids:
        return

    # Clear stale index and rebuild
    db.documents.clear()
    db.embeddings.clear()

    # Load all documents from kb_documents folder
    documents = load_kb_documents()

    if not documents:
        print("Warning: No KB documents found in kb_documents/ folder")
        return

    # Add all documents to vector DB
    for doc in documents:
        db.add_document(
            doc["doc_id"],
            doc["content"],
            category=doc["category"]
        )

    print(f"✓ Knowledge base initialized with {len(documents)} documents from kb_documents/")


def get_KB():
    """Get list of available KB document IDs."""
    documents = load_kb_documents()
    return [doc["doc_id"] for doc in documents]
