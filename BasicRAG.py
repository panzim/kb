#!/usr/bin/env python

from langchain_text_splitters import SentenceTransformersTokenTextSplitter
import os
import faiss
import pickle

from utils.vector_database_facade import VectorDatabaseFacade
from utils.document_loader import DocumentLoader

def pickle_read(filename: str):
    with open(filename + ".pkl", "rb") as f:
        loaded_data = pickle.load(f)
    return loaded_data

docs = list(DocumentLoader().load_and_split())
fine_splitter = SentenceTransformersTokenTextSplitter(
    model_name="all-mpnet-base-v2",
    tokens_per_chunk=384,
    chunk_overlap=50  # or chunk_overlap=0 ?
)

model = fine_splitter._model  # fine_splitter._model[1].word_embedding_dimension == 768
query = "philip"
query_embedding = model.encode([query])


doc_loader = DocumentLoader()
vector_database = VectorDatabaseFacade(
    database_directory=os.path.join(os.path.abspath(os.path.curdir), "db"),
    embedding_model=doc_loader.model
)

vector_database.load()
vector_database.index.search(query_embedding, k=10)
# vector_database.documents[994]
r = vector_database.query(query, min_score=-1)
