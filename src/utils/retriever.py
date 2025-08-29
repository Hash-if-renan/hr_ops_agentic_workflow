import os
from pathlib import Path
from typing import List

import faiss
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
)
from llama_index.readers.file import PDFReader
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore
from dotenv import load_dotenv
load_dotenv()

class Retriever:
    def __init__(
        self,
        storage_dir: str = "data/storage",
        faiss_index_path: str = "data/faiss.index",
        embed_model: str = "text-embedding-3-small",
    ):
        self.storage_dir = Path(storage_dir)
        self.faiss_index_path = Path(faiss_index_path)
        self.embed_model_name = embed_model

        self.index = None
        self.vector_store = None

        # ensure dirs exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.faiss_index_path.parent.mkdir(parents=True, exist_ok=True)

    # --------- Build Index from PDFs ---------
    def build_index(self, pdf_dir: str):
        pdf_dir = Path(pdf_dir)
        if not pdf_dir.exists():
            raise FileNotFoundError(f"❌ PDF directory not found: {pdf_dir}")

        docs = []
        for pdf_file in pdf_dir.glob("*.pdf"):
            reader = PDFReader()
            pdf_docs = reader.load_data(file=pdf_file)
            docs.extend(pdf_docs)

        if not docs:
            raise ValueError("❌ No PDFs found to index.")

        # embedding model
        embed_model = OpenAIEmbedding(model=self.embed_model_name,api_key=os.getenv("OPENAI_API_KEY"))

        # figure out embedding dim
        if self.embed_model_name == "text-embedding-3-small":
            embed_dim = 1536
        elif self.embed_model_name == "text-embedding-3-large":
            embed_dim = 3072
        else:
            dummy_vec = embed_model.get_text_embedding("hello world")
            embed_dim = len(dummy_vec)

        # setup FAISS
        faiss_index = faiss.IndexFlatL2(embed_dim)
        self.vector_store = FaissVectorStore(faiss_index=faiss_index)

        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        # LlamaIndex handles chunking automatically here
        self.index = VectorStoreIndex.from_documents(
            docs,
            storage_context=storage_context,
            embed_model=embed_model,
        )

        # persist
        self.index.storage_context.persist(persist_dir=str(self.storage_dir))
        faiss.write_index(faiss_index, str(self.faiss_index_path))

        print(f"✅ Index built with {len(docs)} documents from {pdf_dir}")

    # --------- Load Existing Index ---------
    def load_index(self):
        if not self.storage_dir.exists() or not self.faiss_index_path.exists():
            raise FileNotFoundError("❌ No index found. Run build_index first.")

        faiss_index = faiss.read_index(str(self.faiss_index_path))
        self.vector_store = FaissVectorStore(faiss_index=faiss_index)

        storage_context = StorageContext.from_defaults(
            persist_dir=str(self.storage_dir),
            vector_store=self.vector_store,
        )

        self.index = load_index_from_storage(storage_context)

    # --------- Query ---------
    def query(self, query: str, top_k: int = 3) -> str:
        if self.index is None:
            self.load_index()

        retriever = self.index.as_retriever(similarity_top_k=top_k)
        results = retriever.retrieve(query)
        print(f"Retrieved {len(results)} results for query: {query}")

        return "\n".join(f"CONTEXT: {r.text}" for r in results)



# Example usage (only runs if script is run directly)
if __name__ == "__main__":
    retriever = Retriever()
    retriever.build_index(pdf_dir="data/pdfs")
    result= retriever.query("Can I edit my application after submitting?", top_k=2)
    print(result)
    print(type(result))
    