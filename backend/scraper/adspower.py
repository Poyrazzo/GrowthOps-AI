import os
import requests

class AdsPowerManager:
    """Utility to interface with the local AdsPower API for browser profile isolation."""
    
    def __init__(self):
        # Default to host.docker.internal which resolves to the host machine running AdsPower
        self.api_url = os.environ.get('ADSPOWER_API_URL', 'http://host.docker.internal:50325')
        
    def start_profile(self, profile_id: str) -> str:
        """Starts the browser profile and returns the websocket CDP endpoint."""
        url = f"{self.api_url}/api/v1/browser/start?user_id={profile_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') != 0:
            raise Exception(f"AdsPower failed to start profile: {data.get('msg')}")
            
        return data['data']['ws']['puppeteer']
        
    def stop_profile(self, profile_id: str) -> bool:
        """Stops the active browser profile."""
        url = f"{self.api_url}/api/v1/browser/stop?user_id={profile_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('code') == 0
