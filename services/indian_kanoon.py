import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict
import re

class IndianKanoonService:
    def __init__(self):
        self.base_url = "https://indiankanoon.org"
        self.search_url = f"{self.base_url}/search/"
        
    async def search_cases(self, fact_pattern: str, max_results: int = 10) -> List[Dict]:
        """
        Search Indian Kanoon for cases matching the given fact pattern
        """
        retry_count = 0
        max_retries = 3
        retry_delay = 2
        last_error = None
        
        while retry_count < max_retries:
            try:
                return await self._do_search(fact_pattern, max_results)
            except Exception as e:
                last_error = e
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(retry_delay * retry_count)
                    continue
                raise Exception(f"Failed after {max_retries} retries. Last error: {str(last_error)}")
    
    async def _do_search(self, fact_pattern: str, max_results: int) -> List[Dict]:
        """
        Perform the actual search with error handling
        """
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            query_params = {
                'formInput': fact_pattern,
                'pagenum': 1
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            try:
                async with session.get(self.search_url, 
                                     params=query_params,
                                     headers=headers) as response:
                    if response.status == 429:
                        raise Exception("Rate limited by Indian Kanoon. Please try again later.")
                    elif response.status != 200:
                        raise Exception(f"Failed to fetch results: HTTP {response.status}")
                    
                    html = await response.text()
                    if "Please enable JavaScript" in html:
                        raise Exception("Access blocked. Please try again later.")
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Check for no results
                    no_results = soup.find('div', class_='no_results')
                    if no_results:
                        return []
                    
                    # Extract search results
                    results = []
                    for result in soup.find_all('div', class_='result'):
                        title = result.find('div', class_='title')
                        if not title:
                            continue
                            
                        link = title.find('a')
                        if not link:
                            continue
                            
                        # Extract text snippet
                        snippet = result.find('div', class_='snippet')
                        summary = snippet.get_text().strip() if snippet else ""
                        
                        # Clean up the summary
                        summary = re.sub(r'\s+', ' ', summary)
                        summary = summary.replace('...', '... ')
                        
                        # For now, use a simple relevance score based on keyword matching
                        relevance = self._calculate_simple_relevance(fact_pattern, summary)
                        
                        results.append({
                            'title': title.get_text().strip(),
                            'url': self.base_url + link['href'] if link else "",
                            'summary': summary,
                            'similarity_score': relevance
                        })
                    
                    # Sort by relevance score
                    results.sort(key=lambda x: x['similarity_score'], reverse=True)
                    return results[:max_results]
                    
            except aiohttp.ClientError as e:
                raise Exception(f"Network error while searching Indian Kanoon: {str(e)}")
            except Exception as e:
                raise Exception(f"Error searching Indian Kanoon: {str(e)}")
    
    def _calculate_simple_relevance(self, query: str, text: str) -> float:
        """
        Calculate a simple relevance score based on keyword matching
        """
        try:
            if not text.strip():
                return 0.0
            
            # Convert to lowercase for comparison
            query_words = set(query.lower().split())
            text_words = set(text.lower().split())
            
            # Calculate overlap
            common_words = query_words.intersection(text_words)
            
            # Simple similarity score based on word overlap
            similarity = len(common_words) / max(len(query_words), 1)
            
            return min(similarity + 0.1, 1.0)  # Add small boost and cap at 1.0
            
        except Exception as e:
            print(f"Error calculating relevance: {str(e)}")
            return 0.0 
