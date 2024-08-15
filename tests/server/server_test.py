import asyncio
import time
from fastapi import WebSocketDisconnect
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from tellar.server.model import Message
from tellar.server.server import Server
from tellar.character import Character, Answer


@pytest.fixture
def mock_character():
    char = AsyncMock(spec=Character)
    char.name = "Test Character"
    char.clone.return_value = char

    # Set up answer as a coroutine
    async def mock_answer(*args, **kwargs):
        return Answer(text="Test answer", image=None)

    char.answer.side_effect = mock_answer
    return char


@pytest.fixture
def server(mock_character):
    return Server(mock_character)


@pytest.fixture
def client(server):
    return TestClient(server._Server__app)


def test_read_root(client, mock_character):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"name": mock_character.name}


@patch("requests.get")
def test_read_picture(mock_get, client, mock_character):
    mock_get.return_value.content = b"fake image data"
    mock_character.answer.return_value = Answer(text="", image="http://fake.image.url")

    response = client.get("/picture")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/jpeg"
    assert response.content == b"fake image data"


def test_read_description(client, mock_character):
    response = client.get("/description")
    assert response.status_code == 200
    assert response.json() == "Test answer"

    # Verify that the mock_character.answer method was called with the correct argument
    mock_character.answer.assert_called_once_with(
        "Describe yourself in a few words (no full sentence)."
    )


def test_read_history_empty(client):
    response = client.get("/history/test_user")
    assert response.status_code == 200
    assert response.json() == []


@patch("tellar.server.server.find_free_port")
@patch("tellar.server.server.Discovery")
@patch("uvicorn.run")
def test_start(mock_uvicorn_run, mock_discovery, mock_find_free_port, server):
    mock_find_free_port.side_effect = [8000, 9000]

    server.start()

    mock_discovery.assert_called_once_with(9000, 8000)
    mock_discovery.return_value.start.assert_called_once()
    mock_uvicorn_run.assert_called_once_with(
        server._Server__app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        ws_ping_interval=50,
        ws_ping_timeout=50,
    )
    mock_discovery.return_value.stop.assert_called_once()
