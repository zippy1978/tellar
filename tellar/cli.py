import click
import os
from colorama import Fore, Style
import pyfiglet
from tellar.cache import init_cache
from langchain_core.vectorstores.base import VectorStore

from tellar.character import Character
from tellar.api.server import start_server
from tellar.vectordb import load_vectordb


@click.command()
@click.option("--character", "-c", type=str, required=True, help="character name")
@click.option("--pdf", "-p", type=str, required=True, help="book PDF file path")
@click.option(
    "--language",
    "-l",
    type=str,
    default="english",
    required=False,
    help="language",
    show_default=True,
)
@click.option(
    "--debug", "-d", help="debug mode", is_flag=True, show_default=True, default=False
)
@click.option(
    "--voice", "-v", help="enable voice", is_flag=True, show_default=True, default=False
)
@click.option(
    "--serve",
    "-s",
    help="enable HTTP API mode",
    is_flag=True,
    show_default=True,
    default=False,
)
def cli(character: str, pdf: str, language: str, debug: bool, voice: bool, serve: bool):
    print("Reading book... Please wait")

    # Check OpenAI API key
    if os.getenv("OPENAI_API_KEY") is None:
        print(
            Fore.RED
            + "Please set the OPENAI_API_KEY environment variable."
            + Style.RESET_ALL
        )
        exit(1)

    # Check that the PDF file exists
    if not os.path.isfile(pdf):
        print(Fore.RED + "PDF file not found." + Style.RESET_ALL)
        exit(1)

    home_dir = os.path.expanduser("~")
    user_data_path = os.path.join(home_dir, ".tellar")
    pdf_name = os.path.basename(pdf)
    # Init query cache
    init_cache(os.path.join(user_data_path, "cache", pdf_name))
    # Create / load vector database
    vectordb = load_vectordb(pdf, os.path.join(user_data_path, "db", pdf_name))
    print(pyfiglet.figlet_format(character))
    # Create character
    char = Character(
        name=character,
        retriever=vectordb.as_retriever(),
        char_name=character,
        language=language,
        verbose=debug,
    )
    if serve:
        # Server mode
        __server_mode(vectordb, character, language, debug)
    else:
        # Interactive mode
        __interactive_mode(vectordb, character, language, debug, voice)


def __server_mode(vectordb: VectorStore, character: str, language: str, debug: bool):

    start_server(vectordb, character, language, debug)


def __interactive_mode(vectordb: VectorStore, character: str, language: str, debug: bool, voice: bool):
    
    # Create character
    char = Character(
        name=character,
        retriever=vectordb.as_retriever(),
        char_name=character,
        language=language,
        verbose=debug,
    )
    
    # Prompt loop
    while True:
        print(Style.BRIGHT + Fore.BLUE + "You > " + Style.RESET_ALL, end="")
        message = input()
        print(Style.BRIGHT + Fore.GREEN + char.name + " > " + Style.RESET_ALL, end="")
        answer = char.answer(message)
        print(answer.text)
        if answer.image is not None:
            print(f"[{answer.image}]")
        if voice:
            speech_file_path = char.speak(answer.text)
            # Play the speech file
            os.system(f"afplay {speech_file_path}")


if __name__ == "__main__":
    cli()
