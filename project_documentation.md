# Marvel Character API Project

## Project Structure

project/
├── main.py              # FastAPI application
├── run.py              # Script to run the API
├── test_api.py         # Test script
├── requirements.txt    # Project dependencies
└── .env               # Environment variables

## Dependencies (requirements.txt)

fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.1
python-dotenv==1.0.0

## Environment Setup (.env)

MARVEL_PUBLIC_KEY=your_public_key_here
MARVEL_PRIVATE_KEY=your_private_key_here

## Main Application (main.py)
The main FastAPI application that:
- Connects to Marvel API
- Provides /character endpoint
- Returns random character information
- Includes favicon support
- Has comprehensive error handling and logging

## Run Script (run.py)
Script to start the FastAPI server using uvicorn.

## Test Script (test_api.py)
A script to test the API endpoint and display results in a formatted way.

## Setup Instructions

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Marvel API credentials in .env file

4. Run the API:
   ```bash
   python run.py
   ```

5. In a new terminal, test the API:
   ```bash
   python test_api.py
   ```

## API Response Format
```json
{
    "id": "integer",
    "name": "string",
    "description": "string",
    "thumbnail": "string",
    "comics": {
        "available": "integer",
        "items": [
            {
                "title": "string",
                "resourceURI": "string"
            }
        ]
    },
    "stories": {
        "available": "integer",
        "items": [
            {
                "title": "string",
                "type": "string",
                "resourceURI": "string"
            }
        ]
    },
    "events": {
        "available": "integer",
        "items": [
            {
                "title": "string",
                "resourceURI": "string"
            }
        ]
    },
    "series": {
        "available": "integer",
        "items": [
            {
                "title": "string",
                "resourceURI": "string"
            }
        ]
    }
}
```

## Notes
- The API makes only two calls to the Marvel API:
  1. To get total character count
  2. To get random character details
- All Marvel API URLs are converted to HTTPS
- Includes error handling and logging
- Favicon is embedded in the code
