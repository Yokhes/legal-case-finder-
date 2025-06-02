import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class CacheService:
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.cache_duration = timedelta(days=7)  # Cache results for 7 days
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Ensure the cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _get_cache_path(self, query: str) -> str:
        """Generate a cache file path for a query"""
        # Use a simple hash of the query as the filename
        query_hash = str(hash(query))
        return os.path.join(self.cache_dir, f"{query_hash}.json")
    
    def get(self, query: str) -> Optional[List[Dict]]:
        """
        Retrieve cached results for a query if they exist and are not expired
        """
        cache_path = self._get_cache_path(query)
        
        if not os.path.exists(cache_path):
            return None
            
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > self.cache_duration:
                os.remove(cache_path)  # Remove expired cache
                return None
                
            return cache_data['results']
            
        except Exception as e:
            print(f"Error reading cache: {str(e)}")
            return None
    
    def set(self, query: str, results: List[Dict]):
        """
        Cache the results for a query
        """
        cache_path = self._get_cache_path(query)
        
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'results': results
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Error writing cache: {str(e)}")
    
    def clear_expired(self):
        """
        Clear expired cache entries
        """
        try:
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.json'):
                    continue
                    
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    cached_time = datetime.fromisoformat(cache_data['timestamp'])
                    if datetime.now() - cached_time > self.cache_duration:
                        os.remove(filepath)
                        
                except Exception:
                    # If we can't read the cache file, remove it
                    os.remove(filepath)
                    
        except Exception as e:
            print(f"Error clearing expired cache: {str(e)}") 
