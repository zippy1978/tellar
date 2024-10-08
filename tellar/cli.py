import asyncio
import logging
import click
import os
from colorama import Fore, Style
import pyfiglet
import uvicorn

from tellar.character import Character
from tellar.server.client import Client
from tellar.server.server import Server
from tellar.searchable_document import SearchableDocument

 # Configure logging
stream_handler = logging.StreamHandler()
logging.basicConfig(
    level=logging.CRITICAL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[stream_handler],
    )
logger = logging.getLogger("tellar")
logger.setLevel(logging.INFO)
console_formatter = uvicorn.logging.ColourizedFormatter(
        "{levelprefix} {message}",
        style="{", use_colors=True)
stream_handler.setFormatter(console_formatter)


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
@click.option("--auto", "-a", help="auto mode: look for another tellar on the network and engage in conversation", is_flag=True, show_default=True, default=False)
def cli(character: str, pdf: str, language: str, debug: bool, voice: bool, serve: bool, auto: bool):
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

    # Create searchable document
    searchable_doc = SearchableDocument(pdf)

    print(pyfiglet.figlet_format(character))
    
    # Create character
    char = Character(
        name=character,
        searchable_doc=searchable_doc,
        char_name=character,
        language=language,
        verbose=debug,
    )

    # Auto mode does not work with server mode enabled
    if auto and serve:
        print(Fore.RED + "Auto mode does not work with server mode enabled." + Style.RESET_ALL)
        exit(1)
    
    # Auto mode does not work with interactive mode
    if auto and not serve:
        __auto_mode(char)

    # Start
    if serve:
        # Server mode
        __server_mode(char)
    else:
        # Interactive mode
        __interactive_mode(char, voice)
        
        
def __auto_mode(char: Character):
    client = Client(char)
    client.start()

def __server_mode(char: Character):
    server = Server(char)
    server.start()


def __interactive_mode(char: Character, voice: bool):

    # Prompt loop
    while True:
        print(Style.BRIGHT + Fore.BLUE + "You > " + Style.RESET_ALL, end="")
        message = input()
        print(Style.BRIGHT + Fore.GREEN + char.name + " > " + Style.RESET_ALL, end="")
        answer = asyncio.run(char.answer(message))
        print(answer.text)
        if answer.image is not None:
            print(f"[{answer.image}]")
        if voice:
            speech_file_path = asyncio.run(char.speak(answer.text))
            # Play the speech file
            os.system(f"afplay {speech_file_path}")


if __name__ == "__main__":
    cli()
