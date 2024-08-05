from dataclasses import dataclass
import os
from pathlib import Path
from langchain_openai import ChatOpenAI, OpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_core.retrievers import BaseRetriever
import openai
import json


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
        json_str = json_str.replace('\n', '\\n')
        try:
            return cls.from_json(json.loads(json_str))
        except json.JSONDecodeError:
            return cls(text=f"{json_str}")


class Character:

    def __init__(
        self,
        name: str,
        retriever: BaseRetriever,
        char_name: str,
        language: str,
        goal: str = None,
        verbose: bool = False,
        temp_speech_file_path: Path = None,
    ):
        self.name = name
        self.retriever = retriever
        self.char_name = char_name
        self.language = language
        self.verbose = verbose
        self.chat_history = []
        self.temp_speech_file_path = temp_speech_file_path

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
        Use only {language} to reply.
        Try not to repeat yourself in conversations. Sometimes, open your answers with questions when you need to move forward.
        Take initiatives and think by yourself.
        ALWAYS answer using a RAW JSON formatted response ONLY, formatted like this: {expected_output}
        Where text is your answer, and image is the URL of the image you created using the draw tool (if any).
        """

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", instructions),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )
        model = ChatOpenAI(model="gpt-4o-mini")

        @tool
        def story_tool(query: str) -> str:
            """Useful for when you need to answer questions about your character."""
            return retriever.invoke(query)

        @tool
        def draw(query: str) -> str:
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

        tools = [story_tool, draw]

        self.agent = create_tool_calling_agent(model, tools, prompt)
        self.executor = AgentExecutor(agent=self.agent, tools=tools, verbose=verbose)

    def answer(self, query: str) -> Answer:
        raw_answer = self.executor.invoke(
            {"input": query, "chat_history": self.chat_history}
        )["output"]
        answer = Answer.from_json_str(raw_answer)
        self.chat_history.extend([HumanMessage(content=query), answer.text])
        return answer

    def speak(self, message: str) -> Path:
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
            retriever=self.retriever,
            char_name=self.char_name,
            language=language or self.language,
            goal=goal,
            verbose=self.verbose,
            temp_speech_file_path=self.temp_speech_file_path,
        )
        
    