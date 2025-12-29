#!/usr/bin/env python

from langchain_text_splitters import SentenceTransformersTokenTextSplitter
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
import os
from tqdm import tqdm
from typing import Tuple, Iterator, List, Dict, Any
import faiss
import pickle
from flashrank import Ranker, RerankRequest


def pickle_read(filename: str):
    with open(filename + ".pkl", "rb") as f:
        loaded_data = pickle.load(f)
    return loaded_data

def pickle_write(data, filename: str):
    with open(filename + ".pkl", "wb") as f:
        pickle.dump(data, f)


fine_splitter = SentenceTransformersTokenTextSplitter(
    model_name="all-mpnet-base-v2",
    tokens_per_chunk=384,
    chunk_overlap=50  # or chunk_overlap=0 ?
)

model = fine_splitter._model  # fine_splitter._model[1].word_embedding_dimension == 768

def table_like(string: str) -> float:
    return string.count('|') / len(string)

def chunk_strings(strings, max_size: int):
    """
    Join strings into chunks of at most `max_size` characters.
    Strings longer than `max_size` are kept as single entries.
    """

    result = []
    current_chunk = ""

    for tags, s in strings:
        if len(s) > max_size:
            # stick big table with previous header
            if table_like(s) > 0.01:
                current_chunk += "\n" + s
                result.append(current_chunk)
                current_chunk = ""
            else:
                if current_chunk:
                    result.append(current_chunk)
                    current_chunk = ""
                # try to separate the big chunk using fine splitter (NN)
                ts = fine_splitter.split_text(s)
                if len(ts) > 1:
                    for t in ts:
                        result.append(t)
                else:
                    result.append(s)
        else:
            # Check if adding this string would exceed max_size
            if current_chunk:
                # +1 for space if we already have content
                if len(current_chunk) + 1 + len(s) <= max_size:
                    current_chunk += "\n" + s
                else:
                    result.append(current_chunk)
                    current_chunk = s
            else:
                current_chunk = s

    if current_chunk: result.append(current_chunk)
    return result


from utils.document_loader import DocumentLoader
docs = list(DocumentLoader().load_and_split())
try:
    index = faiss.read_index("basic_rag.faiss")
    meta = pickle_read("meta")
    print("Index read")
except:
    index = faiss.IndexFlatIP(fine_splitter._model[1].word_embedding_dimension)
    meta = {}
    print("Index created")


query = "philip"
query_embedding = model.encode([query])
scores, indexes = index.search(query_embedding, k=100)
print(indexes[0])


for score, idx in list(zip(scores[0], indexes[0])):
    print(score, idx, meta[idx])


ranker = Ranker(max_length=128)

class VectorDatabaseFacade5:
    def __init__(self, database_directory: str, embedding_model: SentenceTransformer):
        self.database_directory = database_directory
        self.embedding_model = embedding_model
        self.index: faiss.IndexFlatIP = None
        self.documents: Dict[int, Document] = None
        self.ranker = Ranker(max_length=128)

    def save_documents(self, docs: Iterator[Document], autosave: bool = True):
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.embedding_model[1].word_embedding_dimension)
        document_index = self.index.ntotal
        self.documents = {}
        for doc in tqdm(docs):
            embeddings = self.embedding_model.encode([doc.page_content], show_progress_bar=False)
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

    def query(self, query: str, min_score=0.001) -> Iterator[Tuple[Document, float]]:
        query_embedding = self.embedding_model.encode([query], show_progress_bar=False)
        scores, indices = self.index.search(query_embedding, k=100)

        # Rerank
        passages = []
        for score, idx in list(zip(scores[0], indices[0])):
            doc: Document = self.documents[idx]
            passages.append(
                {
                    "id": idx,
                    "text": doc.page_content
                }
            )

        ranker_results: List[Any] = self.ranker.rerank(RerankRequest(query=query, passages=passages))
        results = []
        for i, result in enumerate(ranker_results):
            if i > 0 and result['score'] < min_score:
                break
            idx = result["id"]
            doc = self.documents[idx]
            results.append((doc, result['score']))
        return results


doc_loader = DocumentLoader()
vector_database = VectorDatabaseFacade5(
    database_directory=os.path.join(os.path.abspath(os.path.curdir), "db"),
    embedding_model=doc_loader.model
)


vector_database.load()
vector_database.index.search(query_embedding, k=10)
# vector_database.documents[994]
r = vector_database.query(query, min_score=-1)
