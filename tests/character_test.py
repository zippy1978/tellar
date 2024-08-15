import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from tellar.character import Character, Answer


class TestCharacter:
    @pytest.fixture(autouse=True)
    @patch("tellar.character.ChatOpenAI")
    @patch("tellar.character.create_tool_calling_agent")
    @patch("tellar.character.AgentExecutor")
    def setup(self, mock_agent_executor, mock_create_agent, mock_chat_openai):
        self.mock_searchable_doc = Mock()
        self.mock_model = Mock()
        mock_chat_openai.return_value = self.mock_model
        self.character = Character(
            name="Test",
            searchable_doc=self.mock_searchable_doc,
            char_name="TestChar",
            language="English",
        )

    def test_init(self):
        assert self.character.name == "Test"
        assert self.character.char_name == "TestChar"
        assert self.character.language == "English"
        assert isinstance(self.character.temp_speech_file_path, Path)

    @patch("tellar.character.ChatOpenAI")
    @patch("tellar.character.create_tool_calling_agent")
    @patch("tellar.character.AgentExecutor")
    def test_clone(self, mock_agent_executor, mock_create_agent, mock_chat_openai):
        cloned = self.character.clone(language="French", goal="New Goal")
        assert cloned.name == self.character.name
        assert cloned.language == "French"
        assert cloned.goal == "New Goal"
        assert id(cloned) != id(self.character)

    def test_answer_from_json_str(self):
        json_str = '{"text": "Hello", "image": "http://example.com/image.jpg"}'
        answer = Answer.from_json_str(json_str)
        assert answer.text == "Hello"
        assert answer.image == "http://example.com/image.jpg"

    def test_answer_from_json_str_with_prefix(self):
        json_str = '```json{"text": "Hello", "image": null}```'
        answer = Answer.from_json_str(json_str)
        assert answer.text == "Hello"
        assert answer.image is None

    @pytest.mark.asyncio
    async def test_answer(self):
        self.character.executor = AsyncMock()
        self.character.executor.ainvoke.return_value = {
            "output": '{"text": "Test answer", "image": null}'
        }
        
        answer = await self.character.answer("Test question")
        
        assert isinstance(answer, Answer)
        assert answer.text == "Test answer"
        assert answer.image is None
        assert len(self.character.chat_history) == 2
        
