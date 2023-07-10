from typing import Any
from langchain import LLMChain, OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import RetrievalQA
from langchain.agents import Tool
from langchain.agents.mrkl.base import ZeroShotAgent
from langchain.agents.agent import AgentExecutor

from tellar.prompt import PREFIX, SUFFIX


def create_tellar_agent(retriever: Any, char_name: str, language: str) -> AgentExecutor:

    llm = OpenAI(temperature=0)
    story = RetrievalQA.from_chain_type(
        llm=llm, chain_type="stuff", retriever=retriever)

    tools = [
        Tool(
            name="story_tool",
            func=story.run,
            description="useful for when you need to answer questions about your character.",
        )
    ]

    input_variables = ["input", "agent_scratchpad",
                       "history", "char_name", "language"]
    prompt = ZeroShotAgent.create_prompt(
        tools, prefix=PREFIX, suffix=SUFFIX, input_variables=input_variables)
    partial_prompt = prompt.partial()
    partial_prompt = partial_prompt.partial(
        char_name=char_name, language=language)

    memory = ConversationBufferMemory(
        memory_key="history", return_messages=True)

    llm_chain = LLMChain(
        llm=llm,
        prompt=partial_prompt,
        callback_manager=None,
    )

    tool_names = [tool.name for tool in tools]
    agent = ZeroShotAgent(llm_chain=llm_chain, allowed_tools=tool_names)
    return AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=False,
        memory=memory,
    )
