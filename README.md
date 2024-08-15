# Tellar

Talk to your favorite fictional characters.

## Installation

Python 3.10+ is required.

Install with:

```bash
$ pip3 install tellar@git+https://github.com/zippy1978/tellar
```

## Usage

An OpenAI API key is required to used the tool.

Export it as an environement variable:

```bash
$ export OPENAI_API_KEY=your-key
```

Available options:

```bash
$ tellar --help
Usage: tellar [OPTIONS]

Options:
  -c, --character TEXT  character name  [required]
  -p, --pdf TEXT        book PDF file path  [required]
  -l, --language TEXT   language  [default: english]
  -d, --debug           debug mode
  -v, --voice           enable voice
  -s, --serve           enable HTTP API mode
  --help                Show this message and exit.
```

### Examples:

#### Chat from terminal

```bash
$ tellar -c "Harry Potter" -p harry_potter.pdf -l français
```

#### Serve the API

```bash
$ tellar -c "Harry Potter" -p harry_potter.pdf -l français -s
```

## API Specification


# Server API Documentation

## Endpoints

### Root Endpoint
- **URL:** `/`
- **Method:** `GET`
- **Description:** Returns basic information about the character.
- **Response:** JSON object containing the character's name.

### Character Picture
- **URL:** `/picture`
- **Method:** `GET`
- **Description:** Retrieves a portrait picture of the character.
- **Response:** JPEG image stream.
- **Note:** The image is generated on the first request and cached for subsequent requests.

### Character Description
- **URL:** `/description`
- **Method:** `GET`
- **Description:** Retrieves a brief description of the character.
- **Response:** Plain text description.
- **Note:** The description is generated on the first request and cached for subsequent requests.

### Conversation History
- **URL:** `/history/{char_name}`
- **Method:** `GET`
- **Description:** Retrieves the conversation history for a specific character.
- **Parameters:**
  - `char_name`: The name of the character (string).
- **Response:** JSON array of message objects.
- **Note:** Returns an empty array if no conversation history exists for the specified character.

### WebSocket Connection
- **URL:** `/ws`
- **Protocol:** WebSocket
- **Description:** Establishes a WebSocket connection for real-time communication with the character.
- **Functionality:**
  - Accepts incoming messages in JSON format.
  - Processes messages and generates responses using the character's AI.
  - Sends responses back to the client in JSON format.
  - Maintains separate conversation histories for different users.

## Message Format
Messages exchanged via WebSocket should follow this format:

```json
{
  "sender": "user_identifier",
  "text": "message_content",
  "timestamp": 1234567890,
  "image": null
}
```

## Development environement setup

A venv is recommended to run the project properly (see https://docs.python.org/fr/3/library/venv.html).

### Install dependencies

```bash
$ poetry install
```