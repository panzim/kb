import os
import pickle
import logging
import time
from typing import Dict, List
from typing import Tuple, Iterator

import faiss
from flashrank import Ranker, RerankRequest
from langchain_core.documents import Document
from rerankers.results import Result
from sentence_transformers import SentenceTransformer

class VectorDatabaseFacade:
    def __init__(self, database_directory: str, embedding_model: SentenceTransformer):
        self.database_directory = database_directory
        self.embedding_model = embedding_model
        self.index: faiss.IndexFlatIP = None
        self.documents: Dict[int, Document] = None
        self.ranker = Ranker(max_length=1024, cache_dir=database_directory)
        self.logger = logging.getLogger("vec-db")
        self.logger.info("Reranker dir: %s, llm: %s" % (self.ranker.model_dir, self.ranker.llm_model))

    def save_documents(self, docs: Iterator[Document], autosave: bool = True):
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.embedding_model[1].word_embedding_dimension)
        document_index = self.index.ntotal
        self.documents = {}
        for dcx in docs:
            embeddings = self.embedding_model.encode([dcx.page_content], show_progress_bar=False)
            self.documents[document_index] = dcx
            self.index.add(embeddings)
            dcx.id = document_index
            document_index += 1
        if autosave:
            self.save()

    def save(self):
        if not os.path.exists(self.database_directory):
            os.mkdir(self.database_directory)
        faiss.write_index(self.index, os.path.join(self.database_directory, "document.vectors.faiss"))
        pickle_write(self.documents, os.path.join(self.database_directory, "documents"))

    def load(self):
        self.index = faiss.read_index(os.path.join(self.database_directory, "document.vectors.faiss"))
        self.documents = pickle_read(os.path.join(self.database_directory, "documents"))

    def query(self, query: str, min_score: float = 0.01, limit: int = 10) -> Iterator[Tuple[Document, float]]:
        t1 = time.time()
        query_embedding = self.embedding_model.encode([query], show_progress_bar=False)
        scores, indexes = self.index.search(query_embedding, k=100)

        self.logger.info(f"[BENCHMARK] Vector database cosine search: {time.time() - t1:.2f} s")

        # Rerank
        passages = []
        for score, idx in list(zip(scores[0], indexes[0])):
            dcx: Document = self.documents[idx]
            passages.append(
                {
                    "id": idx,
                    "text": dcx.page_content
                }
            )

        t2 = time.time()
        ranker_results: List[Result] = self.ranker.rerank(RerankRequest(query=query, passages=passages))
        self.logger.info(f"[BENCHMARK] Reranker: {time.time() - t2:.2f} s")
        results = []
        for i, result in enumerate(ranker_results):
            if (i > 0 and result['score'] < min_score) or i > limit:
                break
            idx = result["id"]
            dcx = self.documents[idx]
            results.append((dcx, result['score']))
        return results


def pickle_read(filename: str):
    with open(filename + ".pkl", "rb") as f:
        loaded_data = pickle.load(f)
    return loaded_data

def pickle_write(data, filename: str):
    with open(filename + ".pkl", "wb") as f:
        pickle.dump(data, f)

if __name__ == '__main__':
    from document_loader import DocumentLoader
    doc_loader = DocumentLoader()
    DATABASE_PATH = os.getenv('DATABASE_PATH', os.path.join(os.path.curdir, 'db'))
    vector_database = VectorDatabaseFacade(database_directory=DATABASE_PATH, embedding_model=doc_loader.model)
    vector_database.load()
    for doc in vector_database.query("philip"):
        print(doc)
