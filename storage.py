import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

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