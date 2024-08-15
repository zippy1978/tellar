import pytest
from click.testing import CliRunner
from unittest.mock import call, patch, MagicMock
from tellar.cli import cli

@pytest.fixture
def runner():
    return CliRunner()

@patch('tellar.cli.SearchableDocument')
@patch('tellar.cli.Character')
@patch('tellar.cli.Server')
@patch('tellar.cli.os.path.isfile')
@patch('tellar.cli.os.getenv')
def test_cli_server_mode(mock_getenv, mock_isfile, mock_server, mock_character, mock_searchable_doc, runner):
    mock_getenv.return_value = 'fake_api_key'
    mock_isfile.return_value = True
    mock_server_instance = MagicMock()
    mock_server.return_value = mock_server_instance

    result = runner.invoke(cli, ['--character', 'TestChar', '--pdf', 'test.pdf', '--serve'])

    assert result.exit_code == 0
    mock_searchable_doc.assert_called_once_with('test.pdf')
    mock_character.assert_called_once()
    mock_server.assert_called_once()
    mock_server_instance.start.assert_called_once()


@patch('tellar.cli.os.getenv')
def test_cli_missing_api_key(mock_getenv, runner):
    mock_getenv.return_value = None

    result = runner.invoke(cli, ['--character', 'TestChar', '--pdf', 'test.pdf'])

    assert result.exit_code == 1
    assert "Please set the OPENAI_API_KEY environment variable." in result.output

@patch('tellar.cli.os.getenv')
@patch('tellar.cli.os.path.isfile')
def test_cli_missing_pdf(mock_isfile, mock_getenv, runner):
    mock_getenv.return_value = 'fake_api_key'
    mock_isfile.return_value = False

    result = runner.invoke(cli, ['--character', 'TestChar', '--pdf', 'nonexistent.pdf'])

    assert result.exit_code == 1
    assert "PDF file not found." in result.output
