import asyncio
import logging
import click
import os
from colorama import Fore, Style
import pyfiglet
import uvicorn

from tellar.character import Character
from tellar.server.server import start_server
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

    # Start
    if serve:
        # Server mode
        __server_mode(char)
    else:
        # Interactive mode
        __interactive_mode(char, voice)


def __server_mode(char: Character):

    start_server(char)


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
