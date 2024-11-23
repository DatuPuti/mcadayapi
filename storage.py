import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import httpx

logger = logging.getLogger(__name__)

class MarvelDataStorage:
    def __init__(self):
        self.data_dir = "data"
        self.used_chars_file = os.path.join(self.data_dir, "used_characters.json")
        self.last_response_file = os.path.join(self.data_dir, "last_response.json")
        self.last_call_file = os.path.join(self.data_dir, "last_call.json")
        self._ensure_data_directory()

    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Created data directory: {self.data_dir}")

    def save_character_usage(self, character_id: int):
        """Save character ID with timestamp"""
        try:
            used_chars = self.get_used_characters()
            current_time = datetime.now().isoformat()
            
            used_chars[str(character_id)] = current_time
            
            with open(self.used_chars_file, 'w') as f:
                json.dump(used_chars, f, indent=2)
                
            logger.info(f"Saved character usage: {character_id}")
        except Exception as e:
            logger.error(f"Error saving character usage: {str(e)}")

    def get_used_characters(self) -> Dict[str, str]:
        """Get dictionary of used character IDs and their timestamps"""
        try:
            if os.path.exists(self.used_chars_file):
                with open(self.used_chars_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error reading used characters: {str(e)}")
            return {}

    def is_character_recently_used(self, character_id: int, months: int = 6) -> bool:
        """Check if character was used in the last N months"""
        used_chars = self.get_used_characters()
        if str(character_id) in used_chars:
            last_used = datetime.fromisoformat(used_chars[str(character_id)])
            time_limit = datetime.now() - timedelta(days=30 * months)
            return last_used > time_limit
        return False

    def save_last_response(self, response_data: Dict):
        """Save the last API response"""
        try:
            with open(self.last_response_file, 'w') as f:
                json.dump(response_data, f, indent=2)
            
            # Save the timestamp of the last API call
            timestamp = datetime.now().isoformat()
            with open(self.last_call_file, 'w') as f:
                json.dump({"last_call": timestamp}, f, indent=2)
                
            logger.info("Saved last API response and timestamp")
        except Exception as e:
            logger.error(f"Error saving last response: {str(e)}")

    def get_last_response(self) -> Optional[Dict]:
        """Get the last saved API response"""
        try:
            if os.path.exists(self.last_response_file):
                with open(self.last_response_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error reading last response: {str(e)}")
            return None

    def should_make_new_call(self) -> bool:
        """Check if we should make a new API call (24-hour check)"""
        try:
            if os.path.exists(self.last_call_file):
                with open(self.last_call_file, 'r') as f:
                    data = json.load(f)
                    last_call = datetime.fromisoformat(data["last_call"])
                    time_since_last_call = datetime.now() - last_call
                    return time_since_last_call > timedelta(hours=24)
            return True
        except Exception as e:
            logger.error(f"Error checking last call time: {str(e)}")
            return True

    def cleanup_old_data(self):
        """Clean up old character usage data"""
        try:
            used_chars = self.get_used_characters()
            current_time = datetime.now()
            
            # Remove characters used more than 6 months ago
            cleaned_chars = {
                char_id: timestamp
                for char_id, timestamp in used_chars.items()
                if current_time - datetime.fromisoformat(timestamp) <= timedelta(days=180)
            }
            
            with open(self.used_chars_file, 'w') as f:
                json.dump(cleaned_chars, f, indent=2)
                
            logger.info("Completed character usage cleanup")
        except Exception as e:
            logger.error(f"Error cleaning up character usage data: {str(e)}")

    async def save_related_items(self, character_id: int, character_data: Dict):
        """Save all related items for a character with detailed information"""
        try:
            # First, delete previous related item files
            self._delete_previous_related_files()
            
            # Get and save detailed information for each type
            await self._save_comics_detailed(character_data.get('comics', {}).get('items', []))
            await self._save_stories_detailed(character_data.get('stories', {}).get('items', []))
            await self._save_events_detailed(character_data.get('events', {}).get('items', []))
            await self._save_series_detailed(character_data.get('series', {}).get('items', []))
            
            logger.info(f"Saved all related items for character {character_id}")
        except Exception as e:
            logger.error(f"Error saving related items: {str(e)}")

    def _delete_previous_related_files(self):
        """Delete previous related item files"""
        try:
            related_files = [
                os.path.join(self.data_dir, "comics.json"),
                os.path.join(self.data_dir, "stories.json"),
                os.path.join(self.data_dir, "events.json"),
                os.path.join(self.data_dir, "series.json")
            ]
            
            for file_path in related_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted previous related file: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting previous related files: {str(e)}")

    async def _get_marvel_data(self, url: str) -> Optional[Dict]:
        """Make a call to Marvel API"""
        try:
            # Convert http to https
            url = url.replace('http://', 'https://')
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get auth parameters from main application
                from main import generate_marvel_auth
                params = generate_marvel_auth()
                
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    return response.json()["data"]["results"][0]
                else:
                    logger.error(f"Marvel API error: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching Marvel data: {str(e)}")
            return None

    async def _save_comics_detailed(self, comics: List[Dict]):
        """Save simplified comics information"""
        try:
            detailed_comics = []
            for comic in comics:
                comic_data = await self._get_marvel_data(comic["resourceURI"])
                if comic_data:
                    detailed_comics.append({
                        "id": comic_data["id"],
                        "title": comic_data["title"],
                        "description": comic_data.get("description", "No description available"),
                        "issueNumber": comic_data.get("issueNumber", 0)
                    })

            comics_file = os.path.join(self.data_dir, "comics.json")
            with open(comics_file, 'w') as f:
                json.dump({
                    "saved_at": datetime.now().isoformat(),
                    "items": detailed_comics
                }, f, indent=2)
            logger.info(f"Saved {len(detailed_comics)} simplified comics")
        except Exception as e:
            logger.error(f"Error saving simplified comics: {str(e)}")

    async def _save_stories_detailed(self, stories: List[Dict]):
        """Save simplified stories information"""
        try:
            detailed_stories = []
            for story in stories:
                story_data = await self._get_marvel_data(story["resourceURI"])
                if story_data:
                    detailed_stories.append({
                        "id": story_data["id"],
                        "title": story_data["title"],
                        "description": story_data.get("description", "No description available"),
                        "type": story_data.get("type", "Unknown")
                    })

            stories_file = os.path.join(self.data_dir, "stories.json")
            with open(stories_file, 'w') as f:
                json.dump({
                    "saved_at": datetime.now().isoformat(),
                    "items": detailed_stories
                }, f, indent=2)
            logger.info(f"Saved {len(detailed_stories)} simplified stories")
        except Exception as e:
            logger.error(f"Error saving simplified stories: {str(e)}")

    async def _save_events_detailed(self, events: List[Dict]):
        """Save simplified events information"""
        try:
            detailed_events = []
            for event in events:
                event_data = await self._get_marvel_data(event["resourceURI"])
                if event_data:
                    detailed_events.append({
                        "id": event_data["id"],
                        "title": event_data["title"],
                        "description": event_data.get("description", "No description available"),
                        "start": event_data.get("start", "Unknown"),
                        "end": event_data.get("end", "Unknown")
                    })

            events_file = os.path.join(self.data_dir, "events.json")
            with open(events_file, 'w') as f:
                json.dump({
                    "saved_at": datetime.now().isoformat(),
                    "items": detailed_events
                }, f, indent=2)
            logger.info(f"Saved {len(detailed_events)} simplified events")
        except Exception as e:
            logger.error(f"Error saving simplified events: {str(e)}")

    async def _save_series_detailed(self, series_list: List[Dict]):
        """Save simplified series information"""
        try:
            detailed_series = []
            for series in series_list:
                series_data = await self._get_marvel_data(series["resourceURI"])
                if series_data:
                    detailed_series.append({
                        "id": series_data["id"],
                        "title": series_data["title"],
                        "description": series_data.get("description", "No description available"),
                        "startYear": series_data.get("startYear"),
                        "endYear": series_data.get("endYear")
                    })

            series_file = os.path.join(self.data_dir, "series.json")
            with open(series_file, 'w') as f:
                json.dump({
                    "saved_at": datetime.now().isoformat(),
                    "items": detailed_series
                }, f, indent=2)
            logger.info(f"Saved {len(detailed_series)} simplified series")
        except Exception as e:
            logger.error(f"Error saving simplified series: {str(e)}")

    def get_related_items(self) -> Dict[str, List[Dict]]:
        """Get all related items from saved files"""
        try:
            related_items = {}
            
            # Get comics
            comics_file = os.path.join(self.data_dir, "comics.json")
            if os.path.exists(comics_file):
                with open(comics_file, 'r') as f:
                    related_items['comics'] = json.load(f)['items']
            
            # Get stories
            stories_file = os.path.join(self.data_dir, "stories.json")
            if os.path.exists(stories_file):
                with open(stories_file, 'r') as f:
                    related_items['stories'] = json.load(f)['items']
            
            # Get events
            events_file = os.path.join(self.data_dir, "events.json")
            if os.path.exists(events_file):
                with open(events_file, 'r') as f:
                    related_items['events'] = json.load(f)['items']
            
            # Get series
            series_file = os.path.join(self.data_dir, "series.json")
            if os.path.exists(series_file):
                with open(series_file, 'r') as f:
                    related_items['series'] = json.load(f)['items']
            
            return related_items
        except Exception as e:
            logger.error(f"Error getting related items: {str(e)}")
            return {}