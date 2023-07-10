import click
import os
from colorama import Fore, Style
import pyfiglet
from tellar.agent import create_tellar_agent
from tellar.cache import init_cache

from tellar.vectordb import load_vectordb


@click.command()
@click.option("--character", "-c", type=str, required=True, help="character name")
@click.option("--pdf", "-p", type=str, required=True, help="book PDF file path")
@click.option("--language", "-l", type=str, default="english", required=False, help="language")
def cli(character: str, pdf: str, language: str):
    
    # Check OpenAI API key
    if os.getenv("OPENAI_API_KEY") is None:
        print(Fore.RED + "Please set the OPENAI_API_KEY environment variable." + Style.RESET_ALL)
        exit(1)

    # Check that the PDF file exists
    if not os.path.isfile(pdf):
        print(Fore.RED + "PDF file not found." + Style.RESET_ALL)
        exit(1)

    home_dir = os.path.expanduser('~')
    user_data_path = os.path.join(home_dir, '.tellar')
    pdf_name = os.path.basename(pdf)
    # Init query cache
    init_cache(os.path.join(user_data_path, 'cache', pdf_name))
    # Create / load vector database
    print("Reading book...", end="")
    vectordb = load_vectordb(pdf, os.path.join(user_data_path, 'db', pdf_name))
    print("done.")
    print(pyfiglet.figlet_format(character))
    # Create agent
    agent = create_tellar_agent(
        retriever=vectordb.as_retriever(),
        char_name=character,
        language=language)
    # Prompt loop
    while True:
        print(Style.BRIGHT + Fore.BLUE + "You > " + Style.RESET_ALL, end="")
        message = input()
        print(Style.BRIGHT + Fore.GREEN + character +
              " > " + Style.RESET_ALL, end="")
        print(agent.run(input=message))


if __name__ == "__main__":
    cli()
