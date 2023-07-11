from langchain.document_loaders import PyPDFLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from os.path import exists
from langchain.text_splitter import RecursiveCharacterTextSplitter

def load_vectordb(pdf_path: str, db_path: str):
    embeddings = OpenAIEmbeddings()
    if exists(db_path):
        vectordb = FAISS.load_local(db_path, embeddings)
    else:
        loader = PyPDFLoader(pdf_path)
        pages = loader.load_and_split(text_splitter=RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=0, separators=[" ", ",", "\n"]
        ))
        vectordb = FAISS.from_documents(pages, embeddings)
        vectordb.save_local(db_path)
    return vectordb