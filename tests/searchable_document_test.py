import pytest
import os
from unittest.mock import Mock, patch
from tellar.searchable_document import SearchableDocument
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

@pytest.fixture
def mock_pdf_path():
    return "/path/to/mock.pdf"

@pytest.fixture
def mock_faiss():
    mock = Mock(spec=FAISS)
    mock.as_retriever.return_value = Mock()
    return mock

@patch("tellar.searchable_document.OpenAIEmbeddings")
@patch("tellar.searchable_document.FAISS")
@patch("tellar.searchable_document.PyPDFLoader")
@patch("tellar.searchable_document.exists")
def test_searchable_document_init_existing_db(mock_exists, mock_loader, mock_faiss, mock_embeddings, mock_pdf_path):
    mock_exists.return_value = True
    mock_faiss.load_local.return_value = mock_faiss

    doc = SearchableDocument(mock_pdf_path)

    assert isinstance(doc._SearchableDocument__vector_db, Mock)
    mock_faiss.load_local.assert_called_once()
    mock_loader.assert_not_called()

@patch("tellar.searchable_document.OpenAIEmbeddings")
@patch("tellar.searchable_document.FAISS")
@patch("tellar.searchable_document.PyPDFLoader")
@patch("tellar.searchable_document.exists")
def test_searchable_document_init_new_db(mock_exists, mock_loader, mock_faiss, mock_embeddings, mock_pdf_path):
    mock_exists.return_value = False
    mock_loader.return_value.load_and_split.return_value = [Document(page_content="test content")]
    mock_faiss.from_documents.return_value = mock_faiss

    doc = SearchableDocument(mock_pdf_path)

    assert isinstance(doc._SearchableDocument__vector_db, Mock)
    mock_loader.assert_called_once_with(mock_pdf_path)
    mock_faiss.from_documents.assert_called_once()

def test_search(mock_pdf_path, mock_faiss):
    with patch("tellar.searchable_document.SearchableDocument._SearchableDocument__get_vector_db", return_value=mock_faiss):
        doc = SearchableDocument(mock_pdf_path)
        doc.search("test query")

        doc._SearchableDocument__retriever.invoke.assert_called_once_with("test query")
