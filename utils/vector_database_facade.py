import os
from typing import Dict, List
from typing import Tuple, Iterator

import faiss
from flashrank import Ranker, RerankRequest
from langchain_core.documents import Document
from rerankers.results import Result
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import logging
import time

try:
    from utils.utils import pickle_read, pickle_write
except:
    from utils import pickle_read, pickle_write

class VectorDatabaseFacade:
    def __init__(self, database_directory: str, embedding_model: SentenceTransformer):
        self.database_directory = database_directory
        self.embedding_model = embedding_model
        self.index: faiss.IndexFlatIP = None # (fine_splitter._model[1].word_embedding_dimension)
        self.documents: Dict[int, Document] = None
        self.ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir=database_directory)
        #self.ranker = Ranker(max_length=128)
        self.logger = logging.getLogger("uvicorn")

    def save_documents(self, docs: Iterator[Document], autosave: bool = True):
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.embedding_model[1].word_embedding_dimension)
        document_index = self.index.ntotal
        self.documents = {}
        for doc in tqdm(docs):
            embeddings = self.embedding_model.encode([doc.page_content], show_progress_bar=False)
            # embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            self.documents[document_index] = doc
            self.index.add(embeddings)
            doc.id = document_index
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
        # query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
        scores, indexies = self.index.search(query_embedding, k=100)
        self.logger.info("[BENCHMARK] Vector database cosine search: %.2f" % (time.time() - t1))

        # Rerank
        passages = []
        for score, idx in list(zip(scores[0], indexies[0])):
            doc: Document = self.documents[idx]
            passages.append(
                {
                    "id": idx,
                    "text": doc.page_content
                }
            )

        t2 = time.time()
        runker_results: List[Result] = self.ranker.rerank(RerankRequest(query=query, passages=passages))
        self.logger.info("[BENCHMARK] Reranker: %.2f" % (time.time() - t2))
        results = []
        for i, result in enumerate(runker_results):
            if (i > 0 and result['score'] < min_score) or i > limit:
                break
            idx = result["id"]
            doc = self.documents[idx]
            results.append((doc, result['score']))
        return results

if __name__ == '__main__':
    from document_loader import DocumentLoader
    doc_loader = DocumentLoader()
    DATABASE_PATH = os.getenv('DATABASE_PATH', os.path.join(os.path.curdir, 'db'))
    vector_database = VectorDatabaseFacade(
        database_directory=DATABASE_PATH,
        embedding_model=doc_loader.model
    )
    vector_database.load()
    for doc in vector_database.query("philip"):
        print(doc)
