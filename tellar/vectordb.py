from langchain.document_loaders import PyPDFLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from os.path import exists
from langchain.text_splitter import RecursiveCharacterTextSplitter

def load_vectordb(pdf_path: str, db_path: str):
    embeddings = OpenAIEmbeddings()
    if exists(db_path):
        vectordb = Chroma(persist_directory=db_path,
                          embedding_function=embeddings)
    else:
        loader = PyPDFLoader(pdf_path)
        pages = loader.load_and_split(text_splitter=RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=0, separators=[" ", ",", "\n"]
        ))
        vectordb = Chroma.from_documents(pages, embedding=embeddings,
                                         persist_directory=db_path)
        vectordb.persist()
    return vectordb