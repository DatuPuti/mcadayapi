import httpx
import asyncio
import json
from typing import Optional

async def extract_id_from_uri(resource_uri: str) -> Optional[str]:
    """Extract ID from Marvel API resource URI"""
    try:
        return resource_uri.split('/')[-1]
    except:
        return None

async def test_marvel_api():
    try:
        print("\nTesting Marvel API...")
        print("Making request to http://localhost:8000/character\n")
        
        # Make request to local API for random character
        async with httpx.AsyncClient() as client:
            # Test health check endpoint
            health_response = await client.get("http://localhost:8000/health")
            print("=== Health Check ===")
            print(f"Status: {health_response.json()['status']}")
            print(f"Marvel API: {health_response.json()['marvel_api']}\n")
            
            # Get random character
            response = await client.get("http://localhost:8000/v1/character")
            
            if response.status_code == 200:
                # Get the JSON data
                character_data = response.json()
                
                # Print character information
                print("=== Marvel Character Information ===\n")
                print(f"ID: {character_data['id']}")
                print(f"Name: {character_data['name']}")
                print(f"Description: {character_data['description']}")
                print(f"Thumbnail: {character_data['thumbnail']}\n")
                
                # Test comics endpoint with first comic
                if character_data['comics']['items']:
                    print("=== Testing Comics Endpoint ===")
                    comic = character_data['comics']['items'][0]
                    comic_id = await extract_id_from_uri(comic['resourceURI'])
                    if comic_id:
                        comic_response = await client.get(f"http://localhost:8000/v1/comics/{comic_id}")
                        if comic_response.status_code == 200:
                            comic_data = comic_response.json()
                            print(f"\nComic Title: {comic_data['title']}")
                            print(f"Description: {comic_data['description']}")
                            print(f"Page Count: {comic_data['pageCount']}")
                            print(f"Series: {comic_data['series']}")
                
                # Test series endpoint with first series
                if character_data['series']['items']:
                    print("\n=== Testing Series Endpoint ===")
                    series = character_data['series']['items'][0]
                    series_id = await extract_id_from_uri(series['resourceURI'])
                    if series_id:
                        series_response = await client.get(f"http://localhost:8000/v1/series/{series_id}")
                        if series_response.status_code == 200:
                            series_data = series_response.json()
                            print(f"\nSeries Title: {series_data['title']}")
                            print(f"Description: {series_data['description']}")
                            print(f"Start Year: {series_data['startYear']}")
                            print(f"End Year: {series_data['endYear']}")
                            print(f"Rating: {series_data['rating']}")
                
                # Test events endpoint with first event
                if character_data['events']['items']:
                    print("\n=== Testing Events Endpoint ===")
                    event = character_data['events']['items'][0]
                    event_id = await extract_id_from_uri(event['resourceURI'])
                    if event_id:
                        event_response = await client.get(f"http://localhost:8000/v1/events/{event_id}")
                        if event_response.status_code == 200:
                            event_data = event_response.json()
                            print(f"\nEvent Title: {event_data['title']}")
                            print(f"Description: {event_data['description']}")
                            print(f"Start: {event_data['start']}")
                            print(f"End: {event_data['end']}")
                
                # Test stories endpoint with first story
                if character_data['stories']['items']:
                    print("\n=== Testing Stories Endpoint ===")
                    story = character_data['stories']['items'][0]
                    story_id = await extract_id_from_uri(story['resourceURI'])
                    if story_id:
                        story_response = await client.get(f"http://localhost:8000/v1/stories/{story_id}")
                        if story_response.status_code == 200:
                            story_data = story_response.json()
                            print(f"\nStory Title: {story_data['title']}")
                            print(f"Description: {story_data['description']}")
                            print(f"Type: {story_data['type']}")
                
                # Print summary counts
                print("\n=== Content Summary ===")
                print(f"Comics available: {character_data['comics']['available']}")
                print(f"Stories available: {character_data['stories']['available']}")
                print(f"Events available: {character_data['events']['available']}")
                print(f"Series available: {character_data['series']['available']}")
                
            else:
                print(f"Error: Received status code {response.status_code}")
                print(response.text)
                
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    # Run the async function
    asyncio.run(test_marvel_api()) 