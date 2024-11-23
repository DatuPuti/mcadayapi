import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class MarvelAPIMonitor:
    def __init__(self):
        self.data_dir = "data"
        self.analytics_dir = os.path.join(self.data_dir, "analytics")
        self.logs_dir = os.path.join(self.data_dir, "logs")
        self.stats_file = os.path.join(self.analytics_dir, "api_stats.json")
        self.alerts_file = os.path.join(self.analytics_dir, "alerts.json")
        
        # Ensure directories exist
        Path(self.analytics_dir).mkdir(parents=True, exist_ok=True)
        Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize stats if they don't exist
        self._init_stats()

    def _init_stats(self):
        """Initialize statistics file if it doesn't exist"""
        if not os.path.exists(self.stats_file):
            initial_stats = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "average_response_time": 0,
                "characters_used": 0,
                "last_cleanup": datetime.now().isoformat(),
                "rate_limit_hits": 0,
                "most_requested_characters": {},
                "daily_requests": {},
                "errors": []
            }
            self.save_stats(initial_stats)

    def save_stats(self, stats: Dict):
        """Save statistics to file"""
        with open(self.stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

    def get_stats(self) -> Dict:
        """Get current statistics"""
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading stats: {str(e)}")
            return self._init_stats()

    def log_request(self, character_id: Optional[int], response_time: float, success: bool, error: Optional[str] = None):
        """Log API request details"""
        stats = self.get_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Update general stats
        stats["total_requests"] += 1
        if success:
            stats["successful_requests"] += 1
        else:
            stats["failed_requests"] += 1
            stats["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "error": error
            })
            # Keep only last 100 errors
            stats["errors"] = stats["errors"][-100:]

        # Update response time
        current_avg = stats["average_response_time"]
        stats["average_response_time"] = (current_avg * (stats["total_requests"] - 1) + response_time) / stats["total_requests"]

        # Update daily requests
        stats["daily_requests"][today] = stats["daily_requests"].get(today, 0) + 1

        # Update character usage
        if character_id and success:
            char_id_str = str(character_id)
            stats["most_requested_characters"][char_id_str] = stats["most_requested_characters"].get(char_id_str, 0) + 1

        self.save_stats(stats)
        self._check_alerts(stats)

    def _check_alerts(self, stats: Dict):
        """Check for conditions that require alerts"""
        alerts = []
        
        # Check error rate
        error_rate = stats["failed_requests"] / stats["total_requests"] if stats["total_requests"] > 0 else 0
        if error_rate > 0.1:  # Alert if error rate exceeds 10%
            alerts.append({
                "timestamp": datetime.now().isoformat(),
                "type": "ERROR_RATE",
                "message": f"High error rate detected: {error_rate:.2%}"
            })

        # Check rate limiting
        today = datetime.now().strftime("%Y-%m-%d")
        if stats["daily_requests"].get(today, 0) > 2000:  # Adjust threshold as needed
            alerts.append({
                "timestamp": datetime.now().isoformat(),
                "type": "RATE_LIMIT",
                "message": "Daily request limit approaching"
            })

        if alerts:
            self._save_alerts(alerts)

    def _save_alerts(self, alerts: List[Dict]):
        """Save alerts to file"""
        try:
            existing_alerts = []
            if os.path.exists(self.alerts_file):
                with open(self.alerts_file, 'r') as f:
                    existing_alerts = json.load(f)
            
            # Add new alerts and keep only last 100
            all_alerts = existing_alerts + alerts
            all_alerts = all_alerts[-100:]
            
            with open(self.alerts_file, 'w') as f:
                json.dump(all_alerts, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving alerts: {str(e)}")

    def cleanup_old_data(self):
        """Clean up old data and logs"""
        try:
            stats = self.get_stats()
            
            # Clean up daily requests older than 30 days
            today = datetime.now()
            cutoff_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            stats["daily_requests"] = {
                date: count 
                for date, count in stats["daily_requests"].items() 
                if date >= cutoff_date
            }
            
            # Clean up old errors
            cutoff_time = today - timedelta(days=7)
            stats["errors"] = [
                error for error in stats["errors"]
                if datetime.fromisoformat(error["timestamp"]) > cutoff_time
            ]
            
            # Update cleanup timestamp
            stats["last_cleanup"] = today.isoformat()
            
            self.save_stats(stats)
            logger.info("Completed data cleanup")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}") 