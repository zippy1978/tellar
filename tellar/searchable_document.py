from ast import List
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from os.path import exists
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.retrievers import BaseRetriever

class SearchableDocument:
    def __init__(self, pdf_path: str):
        home_dir = os.path.expanduser("~")
        self.__user_data_path = os.path.join(home_dir, ".tellar")
        self.__vector_db = self.__get_vector_db(pdf_path)
        self.__retriever = self.__vector_db.as_retriever()
        
    def __get_vector_db(self, pdf_path: str) -> FAISS:
        pdf_name = os.path.basename(pdf_path)
        db_path = os.path.join(self.__user_data_path, "db", pdf_name)

        embeddings = OpenAIEmbeddings()
        if exists(db_path):
            vectordb = FAISS.load_local(
                db_path, embeddings, allow_dangerous_deserialization=True
            )
        else:
            loader = PyPDFLoader(pdf_path)
            pages = loader.load_and_split(
                text_splitter=RecursiveCharacterTextSplitter(
                    chunk_size=1000, chunk_overlap=0, separators=[" ", ",", "\n"]
                )
            )
            vectordb = FAISS.from_documents(pages, embeddings)
            vectordb.save_local(db_path)
        return vectordb
    
    def search(self, query: str):
        return self.__retriever.invoke(query)