import glob
import os
from typing import Iterator

from langchain.text_splitter import SentenceTransformersTokenTextSplitter
from langchain_core.documents import Document
from markdown_it import MarkdownIt


class DocumentLoader:
    def __init__(self):
        self.fine_splitter = SentenceTransformersTokenTextSplitter(
            model_name="all-mpnet-base-v2", #"sentence-transformers/all-MiniLM-L6-v2",
            tokens_per_chunk=384,
            chunk_overlap=50
        )
        self.model = self.fine_splitter._model

    # load and split
    def load(self, knowledge_base_path: str = "text-kb") -> Iterator[Document]:
        yield from self.paragraph_parser(self.load_documents(knowledge_base_path))

    def load_documents(self, knowledge_base_path: str = "text-kb") -> Iterator[Document]:
        for filepath in glob.glob(os.path.join(knowledge_base_path, "*.md")):
            filename = os.path.basename(filepath)
            original_filename = filename.removesuffix(".md") + ".pdf"
            with open(filepath) as f:
                yield Document(
                    page_content=f.read(),
                    metadata={"source": original_filename}
                )

    def table_like(self, string: str) -> float:
        return string.count('|') / len(string)

    def chunk_strings(self, strings, max_size: int):
        result = []
        current_chunk = ""

        for tags, s in strings:
            if len(s) > max_size:
                # stick big table with previous header
                if self.table_like(s) > 0.01:
                    current_chunk += "\n" + s
                    result.append(current_chunk)
                    current_chunk = ""
                else:
                    if current_chunk:
                        result.append(current_chunk)
                        current_chunk = ""
                    # try to separate the big chunk using fine splitter (NN)
                    ts = self.fine_splitter.split_text(s)
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

        if current_chunk:
            result.append(current_chunk)

        return result

    def paragraph_parser(self, docs: Iterator[Document], min_chink_size: int = 500, max_chunk_size: int = 1000) -> Iterator[Document]:
        paragraph = [] # header (h2) + text
        paragraph_tags = set()

        for doc in docs:
            md = MarkdownIt()
            tokens = md.parse(doc.page_content)

            stack = []
            chunk_index = 0
            for t in tokens:
                if t.type.endswith('_open'):
                    if t.tag.startswith('h') and len(paragraph_tags) > 1:
                        if paragraph:
                            full_content = "\n".join([p for _, p in paragraph])
                            if len(full_content) > min_chink_size:
                                for chunk in self.chunk_strings(paragraph, max_size=max_chunk_size):
                                    metadata=doc.metadata.copy()
                                    metadata['chunk_index'] = chunk_index
                                    chunk_index += 1
                                    yield Document(
                                        page_content=chunk,
                                        metadata=metadata
                                    )
                            paragraph = []
                            paragraph_tags = set()

                    stack.append(t.tag)
                elif t.type.endswith('_close'):
                    stack.pop()
                elif t.type == 'inline':
                    pass
                elif t.type == 'html_block' and '<!-- image -->' in t.content:
                    continue # ignore images
                else:
                    raise RuntimeError("Unexpected type: %s" % t.type)
                if t.content:
                    paragraph.append([" ".join(stack), t.content])
                if t.tag:
                    paragraph_tags.add(t.tag)
            if paragraph:
                full_content = "\n".join([p for _, p in paragraph])
                if len(full_content) > min_chink_size:
                    for chunk in self.chunk_strings(paragraph, max_size=max_chunk_size):
                        metadata=doc.metadata.copy()
                        metadata['chunk_index'] = chunk_index
                        chunk_index += 1
                        yield Document(
                            page_content=chunk,
                            metadata=metadata
                        )