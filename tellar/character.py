from dataclasses import dataclass
import os
from pathlib import Path
import time
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_core.messages import HumanMessage
import openai
import json

from tellar.searchable_document import SearchableDocument


@dataclass
class Answer:
    text: str = None
    image: str = None

    def to_json(self):
        return {"text": self.text, "image": self.image}

    @classmethod
    def from_json(cls, json: dict):
        text = json.get("text", None)
        image = json.get("image", None)
        return cls(text=text, image=image)

    @classmethod
    def from_json_str(cls, json_str: str):
        # Cleanup: remove eventual "```json" prefix
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        # And eventual "```" suffix
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        # Escape new lines
        # json_str = json_str.replace('\n', '\\n')
        try:
            return cls.from_json(json.loads(json_str))
        except json.JSONDecodeError:
            return cls(text=f"{json_str}")


class Character:

    def __init__(
        self,
        name: str,
        searchable_doc: SearchableDocument,
        char_name: str,
        language: str,
        goal: str = None,
        verbose: bool = False,
        temp_speech_file_path: Path = None,
        model=None,
    ):
        self.name = name
        self.searchable_doc = searchable_doc
        self.char_name = char_name
        self.language = language
        self.goal = goal
        self.verbose = verbose
        self.chat_history = []
        self.temp_speech_file_path = temp_speech_file_path
        self.model = model or ChatOpenAI(model="gpt-4o-mini")

        # If no temp speech file path provided: defaults to local user
        if self.temp_speech_file_path is None:
            home_dir = os.path.expanduser("~")
            user_data_path = os.path.join(home_dir, ".tellar")
            self.temp_speech_file_path = Path(
                os.path.join(user_data_path, "speech.mp3")
            )

        expected_output = """{{"text": "your answer", "image": "image url"}}"""

        instructions = f"""
        Your are {char_name}.
        {goal}
        Use story_tool to learn about your own story (rely exclusively on it to know more about yourself).
        Do speak in the first person from the perspective of {char_name}.
        Do use story_tool to know more about your character.
        Do use time_tool to know the current time.
        Use only {language} to reply.
        You know only what your character knows.
        Try not to repeat yourself in conversations. Sometimes, open your answers with questions when you need to move forward.
        Take initiatives and think by yourself.
        Speak the same way as your character.
        Always draw and think using a style matching the era and universe of your story.
        ALWAYS!!! answer using a RAW JSON (only JSON no plain text aside!) formatted like this: {expected_output}
        Where text is your answer, and image is the URL of the image you created using the draw_tool (if any otherwise set it to null).
        """

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", instructions),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )

        @tool
        def story_tool(query: str) -> str:
            """Useful for when you need to answer questions about your character."""
            return self.searchable_doc.search(query)

        @tool
        def draw_tool(query: str) -> str:
            """Useful for when you need to draw or show something. Returns the URL of the created image"""
            client = openai.OpenAI()
            response = client.images.generate(
                model="dall-e-3",
                prompt=query,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            return response.data[0].url

        @tool
        def time_tool() -> int:
            """Useful for when you need to know the current time"""
            # Return the time formatted to local timezone
            return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime())

        tools = [story_tool, draw_tool, time_tool]

        self.agent = create_tool_calling_agent(self.model, tools, prompt)
        self.executor = AgentExecutor(agent=self.agent, tools=tools, verbose=verbose)

    async def answer(self, query: str) -> Answer:
        raw_answer = await self.executor.ainvoke(
            {"input": query, "chat_history": self.chat_history}
        )
        answer = Answer.from_json_str(raw_answer["output"])
        self.chat_history.extend([HumanMessage(content=query),raw_answer["output"]])
        return answer

    async def speak(self, message: str) -> Path:
        client = openai.OpenAI()
        with client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="onyx",
            # response_format="opus",
            input=message,
        ) as response:
            response.stream_to_file(self.temp_speech_file_path)
        return self.temp_speech_file_path

    def clone(self, language: str = None, goal: str = None):
        return Character(
            name=self.name,
            searchable_doc=self.searchable_doc,
            char_name=self.char_name,
            language=language or self.language,
            goal=goal,
            verbose=self.verbose,
            temp_speech_file_path=self.temp_speech_file_path,
            model=self.model,
        )
