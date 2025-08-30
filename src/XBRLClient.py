import requests
import json
from typing import Dict, Any
from datetime import datetime, timedelta

class XBRLAPIError(Exception):
    """Custom exception for API-specific errors."""
    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class XBRLClient:
    """A client to interact with the XBRL US API, with token management."""

    def __init__(self, client_id: str, client_secret: str, base_url: str = "https://data.xbrl.us/api/v1"):
        """
        Initializes the client with authentication credentials.

        Args:
            client_id (str): Your XBRL application's client ID.
            client_secret (str): Your XBRL application's client secret.
            base_url (str): The base URL for the API.
        """
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry_time = None
        self.session = requests.Session()
        
        # Request an initial token when the client is created
        self._request_new_token()

    def _request_new_token(self):
        """
        Private method to request a new access token from the API.
        This method should be updated with the correct authentication endpoint and logic.
        """
        # Placeholder for the actual API endpoint for token generation
        token_url = "https://auth.xbrl.us/token" 
        
        # The body and headers for the token request will depend on XBRL's OAuth flow
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        try:
            response = requests.post(token_url, data=payload)
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data.get("access_token")
            # The 'expires_in' value is usually in seconds (e.g., 3600 for 1 hour)
            expires_in_seconds = token_data.get("expires_in", 3600) 
            # Set the expiry time with a small buffer (e.g., 5 minutes)
            self.token_expiry_time = datetime.now() + timedelta(seconds=expires_in_seconds - 300)

            print("Access token successfully refreshed.")
        except requests.exceptions.RequestException as e:
            raise XBRLAPIError(f"Failed to retrieve new access token: {e}")

    def _ensure_token_is_valid(self):
        """
        Private method to check if the current token is valid and refresh it if necessary.
        """
        # Check if the token is expired or if it doesn't exist yet
        if not self.access_token or datetime.now() >= self.token_expiry_time:
            self._request_new_token()
            # Update the session header with the new token
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Private method to handle the API response and raise appropriate errors.
        """
        if response.status_code >= 400:
            try:
                error_data = response.json()
            except json.JSONDecodeError:
                error_data = {"error": "Could not parse error message from API."}
            
            message = f"API request failed with status {response.status_code}: {response.reason}"
            if "error" in error_data:
                message += f" - {error_data['error']}"
            
            # If the error is an expired token (status 401 Unauthorized), we may want to handle it
            # This is a good fallback, but our proactive check should prevent it
            if response.status_code == 401 and "expired" in message.lower():
                print("Token expired during request, attempting refresh...")
                self._request_new_token()
                # A more advanced implementation might retry the original request here
            
            raise XBRLAPIError(message, response.status_code, error_data)
        
        return response.json()

    def query(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Performs a GET query to a specified API endpoint, ensuring the token is valid.
        """
        self._ensure_token_is_valid()
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            raise XBRLAPIError(f"Network or request error: {e}") from e

    def __repr__(self) -> str:
        return f"XBRLClient(base_url='{self.base_url}')"