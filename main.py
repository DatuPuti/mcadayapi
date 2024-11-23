from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response, JSONResponse, RedirectResponse
import httpx
import random
import hashlib
import time
import os
import logging
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import traceback
import base64
import sys
from pathlib import Path
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from collections import defaultdict
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import json
from storage import MarvelDataStorage
from datetime import datetime, timedelta
from monitoring import MarvelAPIMonitor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Marvel API credentials
MARVEL_PUBLIC_KEY = os.getenv("MARVEL_PUBLIC_KEY")
MARVEL_PRIVATE_KEY = os.getenv("MARVEL_PRIVATE_KEY")
MARVEL_BASE_URL = "https://gateway.marvel.com/v1/public"

# Add this favicon data near the top of the file after the imports
FAVICON = base64.b64decode(
    'AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAABILAAASCwAAAAAA'
    'AAAAAAD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A'
    '////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD/'
    '//8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP//'
    '/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////'
    'AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A'
    '////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD/'
    '//8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP//'
    '/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////'
    'AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A'
    '////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD/'
    '//8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP//'
    '/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////'
    'AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A'
    '////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD/'
    '//8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP//'
    '/wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////'
    'AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A'
    '////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wA='
)

# Create the FastAPI app first
app = FastAPI(
    title="Marvel Character API",
    description="API for retrieving random Marvel character information",
    version="1.0.0",
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET"],  # Restrict to GET only
            allow_headers=["*"],
        )
    ]
)

# Rate limiting settings
RATE_LIMIT_DURATION = 60  # seconds
RATE_LIMIT_REQUESTS = 30  # requests per duration

# Rate limiting storage
request_counts = defaultdict(list)

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old requests
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip]
        if current_time - req_time < RATE_LIMIT_DURATION
    ]
    
    # Check rate limit
    if len(request_counts[client_ip]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )
    
    # Add current request
    request_counts[client_ip].append(current_time)
    
    return await call_next(request)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

@app.get('/favicon.ico')
async def get_favicon():
    return Response(content=FAVICON, media_type="image/x-icon")

def generate_marvel_auth() -> Dict[str, str]:
    """Generate Marvel API authentication parameters"""
    try:
        if not MARVEL_PUBLIC_KEY or not MARVEL_PRIVATE_KEY:
            raise ValueError("Marvel API credentials not found in environment variables")
        
        ts = str(int(time.time()))
        hash_string = ts + MARVEL_PRIVATE_KEY + MARVEL_PUBLIC_KEY
        hash_value = hashlib.md5(hash_string.encode()).hexdigest()
        
        return {
            "ts": ts,
            "apikey": MARVEL_PUBLIC_KEY,
            "hash": hash_value
        }
    except Exception as e:
        logger.error(f"Error generating Marvel auth: {str(e)}")
        raise

async def get_total_characters() -> int:
    """Get total number of Marvel characters"""
    try:
        async with httpx.AsyncClient() as client:
            params = generate_marvel_auth()
            params["limit"] = 1
            
            logger.info(f"Making request to {MARVEL_BASE_URL}/characters")
            response = await client.get(f"{MARVEL_BASE_URL}/characters", params=params)
            
            if response.status_code != 200:
                logger.error(f"Marvel API error: {response.text}")
                raise HTTPException(status_code=response.status_code, 
                                 detail=f"Marvel API error: {response.text}")
            
            data = response.json()
            logger.info(f"Total characters found: {data['data']['total']}")
            return data["data"]["total"]
    except Exception as e:
        logger.error(f"Error getting total characters: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def validate_character_id(character_id: int) -> bool:
    """Validate character ID is within acceptable range"""
    return 1000000 <= character_id <= 2000000  # Adjust range as needed

async def get_character_details(character_id: int) -> Dict[str, Any]:
    """Get detailed information about a character"""
    try:
        if not validate_character_id(character_id):
            raise ValueError(f"Invalid character ID: {character_id}")
            
        async with httpx.AsyncClient() as client:
            params = generate_marvel_auth()
            
            # Get character base info
            logger.info(f"Getting details for character ID: {character_id}")
            response = await client.get(f"{MARVEL_BASE_URL}/characters/{character_id}", params=params)
            if response.status_code != 200:
                logger.error(f"Marvel API error: {response.text}")
                raise HTTPException(status_code=response.status_code, 
                                 detail=f"Marvel API error: {response.text}")
            
            character_data = response.json()["data"]["results"][0]
            
            # Prepare the response data using only the data we already have
            character_info = {
                "id": character_data["id"],
                "name": character_data["name"],
                "description": character_data["description"] or "No description available",
                "thumbnail": f"{character_data['thumbnail']['path']}.{character_data['thumbnail']['extension']}",
                "comics": {
                    "available": character_data["comics"]["available"],
                    "items": [
                        {
                            "title": comic["name"],
                            "resourceURI": comic["resourceURI"].replace('http://', 'https://')
                        }
                        for comic in character_data["comics"]["items"]
                    ]
                },
                "stories": {
                    "available": character_data["stories"]["available"],
                    "items": [
                        {
                            "title": story["name"],
                            "type": story["type"],
                            "resourceURI": story["resourceURI"].replace('http://', 'https://')
                        }
                        for story in character_data["stories"]["items"]
                    ]
                },
                "events": {
                    "available": character_data["events"]["available"],
                    "items": [
                        {
                            "title": event["name"],
                            "resourceURI": event["resourceURI"].replace('http://', 'https://')
                        }
                        for event in character_data["events"]["items"]
                    ]
                },
                "series": {
                    "available": character_data["series"]["available"],
                    "items": [
                        {
                            "title": series["name"],
                            "resourceURI": series["resourceURI"].replace('http://', 'https://')
                        }
                        for series in character_data["series"]["items"]
                    ]
                }
            }
            
            return character_info
            
    except Exception as e:
        logger.error(f"Error in get_character_details: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_comic_details(comic_id: str) -> Dict[str, Any]:
    """Get detailed information about a comic"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = generate_marvel_auth()
            
            logger.info(f"Getting details for comic ID: {comic_id}")
            response = await client.get(f"{MARVEL_BASE_URL}/comics/{comic_id}", params=params)
            
            if response.status_code != 200:
                logger.error(f"Marvel API error: {response.text}")
                raise HTTPException(status_code=response.status_code, 
                                 detail=f"Marvel API error: {response.text}")
            
            comic_data = response.json()["data"]["results"][0]
            return {
                "id": comic_data["id"],
                "title": comic_data["title"],
                "description": comic_data.get("description", "No description available"),
                "thumbnail": f"{comic_data['thumbnail']['path']}.{comic_data['thumbnail']['extension']}",
                "pageCount": comic_data.get("pageCount", 0),
                "series": comic_data.get("series", {}).get("name", "Unknown series"),
                "dates": comic_data.get("dates", []),
                "prices": comic_data.get("prices", [])
            }
    except Exception as e:
        logger.error(f"Error getting comic details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_series_details(series_id: str) -> Dict[str, Any]:
    """Get detailed information about a series"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = generate_marvel_auth()
            
            logger.info(f"Getting details for series ID: {series_id}")
            response = await client.get(f"{MARVEL_BASE_URL}/series/{series_id}", params=params)
            
            if response.status_code != 200:
                logger.error(f"Marvel API error: {response.text}")
                raise HTTPException(status_code=response.status_code, 
                                 detail=f"Marvel API error: {response.text}")
            
            series_data = response.json()["data"]["results"][0]
            return {
                "id": series_data["id"],
                "title": series_data["title"],
                "description": series_data.get("description", "No description available"),
                "thumbnail": f"{series_data['thumbnail']['path']}.{series_data['thumbnail']['extension']}",
                "startYear": series_data.get("startYear"),
                "endYear": series_data.get("endYear"),
                "rating": series_data.get("rating", "Unknown"),
                "type": series_data.get("type", "Unknown")
            }
    except Exception as e:
        logger.error(f"Error getting series details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_event_details(event_id: str) -> Dict[str, Any]:
    """Get detailed information about an event"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = generate_marvel_auth()
            
            logger.info(f"Getting details for event ID: {event_id}")
            response = await client.get(f"{MARVEL_BASE_URL}/events/{event_id}", params=params)
            
            if response.status_code != 200:
                logger.error(f"Marvel API error: {response.text}")
                raise HTTPException(status_code=response.status_code, 
                                 detail=f"Marvel API error: {response.text}")
            
            event_data = response.json()["data"]["results"][0]
            return {
                "id": event_data["id"],
                "title": event_data["title"],
                "description": event_data.get("description", "No description available"),
                "thumbnail": f"{event_data['thumbnail']['path']}.{event_data['thumbnail']['extension']}",
                "start": event_data.get("start", "Unknown"),
                "end": event_data.get("end", "Unknown"),
                "modified": event_data.get("modified")
            }
    except Exception as e:
        logger.error(f"Error getting event details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_story_details(story_id: str) -> Dict[str, Any]:
    """Get detailed information about a story"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = generate_marvel_auth()
            
            logger.info(f"Getting details for story ID: {story_id}")
            response = await client.get(f"{MARVEL_BASE_URL}/stories/{story_id}", params=params)
            
            if response.status_code != 200:
                logger.error(f"Marvel API error: {response.text}")
                raise HTTPException(status_code=response.status_code, 
                                 detail=f"Marvel API error: {response.text}")
            
            story_data = response.json()["data"]["results"][0]
            return {
                "id": story_data["id"],
                "title": story_data["title"],
                "description": story_data.get("description", "No description available"),
                "type": story_data.get("type", "Unknown"),
                "modified": story_data.get("modified")
            }
    except Exception as e:
        logger.error(f"Error getting story details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add this after the FastAPI app creation
storage = MarvelDataStorage()

# Add version prefix to routes
api_v1 = FastAPI(
    title="Marvel Character API v1",
    description="Version 1 of the Marvel Character API",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "characters",
            "description": "Operations with Marvel characters"
        }
    ]
)

# Then define the routes
@api_v1.get("/character", tags=["characters"])
async def get_random_character():
    """Get a random Marvel character with their details."""
    try:
        # Check if we should use cached response
        if not storage.should_make_new_call():
            logger.info("Using cached response (within 24-hour period)")
            cached_response = storage.get_last_response()
            if cached_response:
                return cached_response
        
        # Get total number of characters
        total_characters = await get_total_characters()
        
        # Keep trying until we find an unused character
        max_attempts = 50  # Prevent infinite loop
        attempts = 0
        
        while attempts < max_attempts:
            # Generate random offset
            offset = random.randint(0, total_characters - 1)
            logger.info(f"Generated random offset: {offset}")
            
            # Get character at random offset
            async with httpx.AsyncClient() as client:
                params = generate_marvel_auth()
                params["limit"] = 1
                params["offset"] = offset
                
                logger.info(f"Making request to get character at offset {offset}")
                response = await client.get(f"{MARVEL_BASE_URL}/characters", params=params)
                
                if response.status_code != 200:
                    logger.error(f"Marvel API error: {response.text}")
                    raise HTTPException(status_code=response.status_code, 
                                     detail=f"Marvel API error: {response.text}")
                
                character_data = response.json()
                attribution_info = {
                    "attributionText": character_data["attributionText"],
                    "attributionHTML": character_data["attributionHTML"],
                    "copyright": character_data["copyright"]
                }
                
                character_result = character_data["data"]["results"][0]
                character_id = character_result["id"]
                
                # Check if character was recently used
                if not storage.is_character_recently_used(character_id):
                    logger.info(f"Found unused character: {character_result['name']} (ID: {character_id})")
                    
                    # Get detailed character information
                    character_info = await get_character_details(character_id)
                    
                    # Add attribution information
                    final_response = {
                        **attribution_info,
                        "data": character_info
                    }
                    
                    # Save the character usage, response, and related items
                    storage.save_character_usage(character_id)
                    storage.save_last_response(final_response)
                    await storage.save_related_items(character_id, character_info)
                    
                    return final_response
                
                logger.info(f"Character {character_id} was recently used, trying another...")
                attempts += 1
        
        raise HTTPException(
            status_code=503,
            detail="Could not find an unused character after multiple attempts"
        )
            
    except Exception as e:
        logger.error(f"Error in get_random_character: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@api_v1.get("/comics", tags=["related-items"])
async def get_saved_comics():
    """Get saved comics information for the last fetched character"""
    try:
        comics_file = os.path.join(storage.data_dir, "comics.json")
        if os.path.exists(comics_file):
            with open(comics_file, 'r') as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail="No saved comics data found")
    except Exception as e:
        logger.error(f"Error reading saved comics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_v1.get("/stories", tags=["related-items"])
async def get_saved_stories():
    """Get saved stories information for the last fetched character"""
    try:
        stories_file = os.path.join(storage.data_dir, "stories.json")
        if os.path.exists(stories_file):
            with open(stories_file, 'r') as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail="No saved stories data found")
    except Exception as e:
        logger.error(f"Error reading saved stories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_v1.get("/events", tags=["related-items"])
async def get_saved_events():
    """Get saved events information for the last fetched character"""
    try:
        events_file = os.path.join(storage.data_dir, "events.json")
        if os.path.exists(events_file):
            with open(events_file, 'r') as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail="No saved events data found")
    except Exception as e:
        logger.error(f"Error reading saved events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_v1.get("/series", tags=["related-items"])
async def get_saved_series():
    """Get saved series information for the last fetched character"""
    try:
        series_file = os.path.join(storage.data_dir, "series.json")
        if os.path.exists(series_file):
            with open(series_file, 'r') as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail="No saved series data found")
    except Exception as e:
        logger.error(f"Error reading saved series: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_v1.get("/all", tags=["related-items"])
async def get_all_saved_related():
    """Get all saved related items for the last fetched character"""
    try:
        related_items = storage.get_related_items()
        if related_items:
            return {
                "saved_at": datetime.now().isoformat(),
                "data": related_items
            }
        raise HTTPException(status_code=404, detail="No saved related items found")
    except Exception as e:
        logger.error(f"Error reading saved related items: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 

# Finally, mount the v1 routes
app.mount("/v1", api_v1)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"]) 

# Then define the credentials check functions
async def test_credentials():
    """Test Marvel API credentials with a simple API call"""
    async with httpx.AsyncClient() as client:
        params = generate_marvel_auth()
        response = await client.get(f"{MARVEL_BASE_URL}/characters", params=params)
        if response.status_code != 200:
            raise ValueError(f"Invalid credentials: {response.json().get('message', 'Unknown error')}")

def check_credentials():
    """Verify API credentials are properly set up"""
    try:
        if not MARVEL_PUBLIC_KEY or not MARVEL_PRIVATE_KEY:
            raise ValueError("Marvel API credentials not found")
        
        if len(MARVEL_PUBLIC_KEY) != 32 or len(MARVEL_PRIVATE_KEY) != 40:
            raise ValueError("Invalid Marvel API key format")
            
        logger.info("Marvel API credentials format verified")
        
    except Exception as e:
        logger.error(f"Credential verification failed: {str(e)}")
        error_message = """
Error: Marvel API credential verification failed!

Please ensure:
1. You have valid Marvel API credentials
2. Your .env file contains:
   MARVEL_PUBLIC_KEY=your_32_character_public_key
   MARVEL_PRIVATE_KEY=your_40_character_private_key
3. Your credentials have the necessary permissions
4. You haven't exceeded API rate limits

Never share or commit your .env file!"""
        print(error_message)
        sys.exit(1)

# Initial credential format check
check_credentials()

# Now we can use the app variable
@app.on_event("startup")
async def startup_event():
    """Verify API credentials on startup"""
    try:
        await test_credentials()
        logger.info("Marvel API credentials verified successfully")
    except Exception as e:
        logger.error(f"API credential verification failed: {str(e)}")
        sys.exit(1) 

# Add this after the logging setup
if os.getenv("PRODUCTION"):
    logger.warning("""
=====================================================
Running in PRODUCTION mode - Ensure secure credentials
=====================================================
""")
else:
    logger.info("""
=====================================================
Running in DEVELOPMENT mode
Warning: Using development credentials
Do not use these credentials in production!
=====================================================
""") 

# Add a request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log request details
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host,
                "status_code": response.status_code,
                "duration_ms": duration * 1000
            }
            logger.info(f"Request: {json.dumps(log_entry)}")
            
            # Update monitoring stats
            character_id = None
            if request.url.path == "/v1/character":
                # Extract character ID from response if available
                try:
                    body = response.body()
                    if body:
                        data = json.loads(body)
                        character_id = data.get("id")
                except:
                    pass
            
            monitor.log_request(
                character_id=character_id,
                response_time=duration,
                success=response.status_code < 400
            )
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Request failed: {str(e)}")
            monitor.log_request(
                character_id=None,
                response_time=duration,
                success=False,
                error=str(e)
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )

# Add more security headers
class EnhancedSecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Server": "Marvel Character API"
        })
        return response

# Add the middlewares
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(EnhancedSecurityHeadersMiddleware) 

@app.get("/health")
async def health_check():
    """API health check endpoint"""
    try:
        # Test Marvel API connection
        await test_credentials()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "marvel_api": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "marvel_api": str(e)
        } 

# Add this near the other routes
@app.get("/")
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")

# Add this import at the top
from fastapi.responses import RedirectResponse 

@app.get("/character")
async def legacy_character():
    """Redirect old endpoint to new versioned endpoint"""
    return RedirectResponse(url="/v1/character") 

# Initialize monitor after storage
monitor = MarvelAPIMonitor()

# Add new endpoints
@app.get("/stats", tags=["monitoring"])
async def get_api_stats():
    """Get API usage statistics"""
    return monitor.get_stats()

@app.get("/alerts", tags=["monitoring"])
async def get_alerts():
    """Get API alerts"""
    try:
        with open(monitor.alerts_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Add cleanup task
@app.on_event("startup")
async def schedule_cleanup():
    """Schedule periodic data cleanup"""
    async def cleanup_task():
        while True:
            await asyncio.sleep(24 * 60 * 60)  # Run daily
            storage.cleanup_old_data()
            monitor.cleanup_old_data()
    
    asyncio.create_task(cleanup_task()) 

# Add these new endpoints after the existing ones

@api_v1.get("/comics/{comic_id}", tags=["comics"])
async def get_comic(comic_id: str):
    """Get detailed information about a specific comic"""
    return await get_comic_details(comic_id)

@api_v1.get("/series/{series_id}", tags=["series"])
async def get_series(series_id: str):
    """Get detailed information about a specific series"""
    return await get_series_details(series_id)

@api_v1.get("/events/{event_id}", tags=["events"])
async def get_event(event_id: str):
    """Get detailed information about a specific event"""
    return await get_event_details(event_id)

@api_v1.get("/stories/{story_id}", tags=["stories"])
async def get_story(story_id: str):
    """Get detailed information about a specific story"""
    return await get_story_details(story_id) 