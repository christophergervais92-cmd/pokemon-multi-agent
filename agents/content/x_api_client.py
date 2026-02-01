"""
X/Twitter API Client for posting and managing tweets.
Supports Twitter API v2 with OAuth 1.0a and OAuth 2.0 authentication.
"""

import os
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
import requests


@dataclass
class XCredentials:
    """X/Twitter API credentials."""
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    access_token_secret: str = ""
    bearer_token: str = ""
    
    @classmethod
    def from_env(cls) -> 'XCredentials':
        """Load credentials from environment variables."""
        return cls(
            api_key=os.environ.get("X_API_KEY", os.environ.get("TWITTER_API_KEY", "")),
            api_secret=os.environ.get("X_API_SECRET", os.environ.get("TWITTER_API_SECRET", "")),
            access_token=os.environ.get("X_ACCESS_TOKEN", os.environ.get("TWITTER_ACCESS_TOKEN", "")),
            access_token_secret=os.environ.get("X_ACCESS_TOKEN_SECRET", os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")),
            bearer_token=os.environ.get("X_BEARER_TOKEN", os.environ.get("TWITTER_BEARER_TOKEN", ""))
        )
    
    def is_valid(self) -> bool:
        """Check if credentials are configured."""
        return bool(self.api_key and self.api_secret and self.access_token and self.access_token_secret)


@dataclass
class Tweet:
    """Represents a tweet."""
    id: str = ""
    text: str = ""
    created_at: str = ""
    author_id: str = ""
    metrics: Dict = field(default_factory=dict)
    url: str = ""


@dataclass
class PostResult:
    """Result of posting a tweet."""
    success: bool
    tweet_id: Optional[str] = None
    tweet_url: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict] = None


class XAPIClient:
    """
    X/Twitter API client for posting and managing content.
    
    Features:
    - Post tweets with text and media
    - Schedule tweets
    - Reply to tweets
    - Quote tweets
    - Delete tweets
    - Get tweet metrics
    - Rate limit handling
    """
    
    API_BASE = "https://api.twitter.com"
    API_VERSION = "2"
    
    def __init__(self, credentials: Optional[XCredentials] = None):
        """Initialize the X API client."""
        self.credentials = credentials or XCredentials.from_env()
        self.session = requests.Session()
        self._rate_limits = {}
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Minimum seconds between requests
    
    def _generate_oauth_signature(
        self,
        method: str,
        url: str,
        params: Dict,
        oauth_params: Dict
    ) -> str:
        """Generate OAuth 1.0a signature."""
        # Combine all parameters
        all_params = {**params, **oauth_params}
        
        # Sort and encode parameters
        sorted_params = sorted(all_params.items())
        param_string = "&".join(
            f"{urllib.parse.quote(str(k), safe='')}"
            f"={urllib.parse.quote(str(v), safe='')}"
            for k, v in sorted_params
        )
        
        # Create signature base string
        signature_base = "&".join([
            method.upper(),
            urllib.parse.quote(url, safe=''),
            urllib.parse.quote(param_string, safe='')
        ])
        
        # Create signing key
        signing_key = "&".join([
            urllib.parse.quote(self.credentials.api_secret, safe=''),
            urllib.parse.quote(self.credentials.access_token_secret, safe='')
        ])
        
        # Generate signature
        signature = hmac.new(
            signing_key.encode('utf-8'),
            signature_base.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _generate_oauth_header(self, method: str, url: str, params: Dict = None) -> str:
        """Generate OAuth 1.0a authorization header."""
        params = params or {}
        
        oauth_params = {
            'oauth_consumer_key': self.credentials.api_key,
            'oauth_nonce': base64.b64encode(os.urandom(32)).decode('utf-8').replace('=', '').replace('+', '').replace('/', ''),
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_token': self.credentials.access_token,
            'oauth_version': '1.0'
        }
        
        oauth_params['oauth_signature'] = self._generate_oauth_signature(
            method, url, params, oauth_params
        )
        
        auth_header = 'OAuth ' + ', '.join(
            f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        )
        
        return auth_header
    
    def _wait_for_rate_limit(self):
        """Ensure minimum time between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        json_data: Dict = None,
        use_bearer: bool = False
    ) -> Dict:
        """Make an authenticated request to the X API."""
        url = f"{self.API_BASE}/{self.API_VERSION}/{endpoint}"
        
        self._wait_for_rate_limit()
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        if use_bearer and self.credentials.bearer_token:
            headers['Authorization'] = f'Bearer {self.credentials.bearer_token}'
        else:
            headers['Authorization'] = self._generate_oauth_header(method, url, params or {})
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30
            )
            
            # Store rate limit info
            self._rate_limits[endpoint] = {
                'limit': response.headers.get('x-rate-limit-limit'),
                'remaining': response.headers.get('x-rate-limit-remaining'),
                'reset': response.headers.get('x-rate-limit-reset')
            }
            
            if response.status_code == 429:
                # Rate limited - wait and retry
                reset_time = int(response.headers.get('x-rate-limit-reset', time.time() + 60))
                wait_time = max(reset_time - time.time(), 1)
                time.sleep(min(wait_time, 60))  # Wait max 60 seconds
                return self._make_request(method, endpoint, params, json_data, use_bearer)
            
            return {
                'success': response.status_code in [200, 201],
                'status_code': response.status_code,
                'data': response.json() if response.text else {},
                'headers': dict(response.headers)
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    
    def post_tweet(
        self,
        text: str,
        reply_to: Optional[str] = None,
        quote_tweet_id: Optional[str] = None,
        media_ids: Optional[List[str]] = None,
        poll_options: Optional[List[str]] = None,
        poll_duration_minutes: int = 60
    ) -> PostResult:
        """
        Post a tweet.
        
        Args:
            text: Tweet text (max 280 characters)
            reply_to: Tweet ID to reply to
            quote_tweet_id: Tweet ID to quote
            media_ids: List of media IDs to attach
            poll_options: List of poll options (2-4 options)
            poll_duration_minutes: Poll duration in minutes
            
        Returns:
            PostResult with tweet details
        """
        if not self.credentials.is_valid():
            return PostResult(
                success=False,
                error="X API credentials not configured. Set X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET environment variables."
            )
        
        if len(text) > 280:
            return PostResult(
                success=False,
                error=f"Tweet too long ({len(text)} chars). Max 280 characters."
            )
        
        payload = {"text": text}
        
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}
        
        if quote_tweet_id:
            payload["quote_tweet_id"] = quote_tweet_id
        
        if media_ids:
            payload["media"] = {"media_ids": media_ids}
        
        if poll_options and len(poll_options) >= 2:
            payload["poll"] = {
                "options": poll_options[:4],
                "duration_minutes": poll_duration_minutes
            }
        
        result = self._make_request("POST", "tweets", json_data=payload)
        
        if result.get('success') and result.get('data', {}).get('data'):
            tweet_data = result['data']['data']
            tweet_id = tweet_data.get('id', '')
            return PostResult(
                success=True,
                tweet_id=tweet_id,
                tweet_url=f"https://twitter.com/i/web/status/{tweet_id}" if tweet_id else None,
                data=tweet_data
            )
        else:
            error = result.get('error') or result.get('data', {}).get('detail') or result.get('data', {}).get('errors', [{}])[0].get('message', 'Unknown error')
            return PostResult(
                success=False,
                error=error,
                data=result.get('data')
            )
    
    def delete_tweet(self, tweet_id: str) -> bool:
        """Delete a tweet by ID."""
        if not self.credentials.is_valid():
            return False
        
        result = self._make_request("DELETE", f"tweets/{tweet_id}")
        return result.get('success', False)
    
    def get_tweet(self, tweet_id: str, include_metrics: bool = True) -> Optional[Tweet]:
        """Get a tweet by ID."""
        params = {}
        if include_metrics:
            params['tweet.fields'] = 'created_at,public_metrics,author_id'
        
        result = self._make_request("GET", f"tweets/{tweet_id}", params=params, use_bearer=True)
        
        if result.get('success') and result.get('data', {}).get('data'):
            data = result['data']['data']
            return Tweet(
                id=data.get('id', ''),
                text=data.get('text', ''),
                created_at=data.get('created_at', ''),
                author_id=data.get('author_id', ''),
                metrics=data.get('public_metrics', {}),
                url=f"https://twitter.com/i/web/status/{data.get('id', '')}"
            )
        return None
    
    def get_me(self) -> Optional[Dict]:
        """Get authenticated user info."""
        result = self._make_request(
            "GET", 
            "users/me",
            params={'user.fields': 'id,name,username,profile_image_url,public_metrics'}
        )
        
        if result.get('success'):
            return result.get('data', {}).get('data')
        return None
    
    def reply_to_tweet(self, tweet_id: str, text: str) -> PostResult:
        """Reply to a specific tweet."""
        return self.post_tweet(text=text, reply_to=tweet_id)
    
    def quote_tweet(self, tweet_id: str, text: str) -> PostResult:
        """Quote a tweet with additional commentary."""
        return self.post_tweet(text=text, quote_tweet_id=tweet_id)
    
    def create_thread(self, tweets: List[str]) -> List[PostResult]:
        """
        Create a thread of tweets.
        
        Args:
            tweets: List of tweet texts (posted in order)
            
        Returns:
            List of PostResults for each tweet
        """
        results = []
        previous_tweet_id = None
        
        for tweet_text in tweets:
            result = self.post_tweet(
                text=tweet_text,
                reply_to=previous_tweet_id
            )
            results.append(result)
            
            if result.success:
                previous_tweet_id = result.tweet_id
            else:
                # Stop thread if a tweet fails
                break
        
        return results
    
    def get_rate_limits(self) -> Dict:
        """Get current rate limit status."""
        return self._rate_limits.copy()
    
    def verify_credentials(self) -> Dict:
        """Verify API credentials are working."""
        if not self.credentials.is_valid():
            return {
                'valid': False,
                'error': 'Credentials not configured'
            }
        
        user = self.get_me()
        if user:
            return {
                'valid': True,
                'user': user
            }
        return {
            'valid': False,
            'error': 'Could not verify credentials'
        }


class MockXAPIClient(XAPIClient):
    """
    Mock X API client for testing without actual API calls.
    """
    
    def __init__(self):
        super().__init__(XCredentials())
        self._mock_tweets = []
        self._tweet_counter = 1000000000000000000
    
    def post_tweet(self, text: str, **kwargs) -> PostResult:
        """Mock posting a tweet."""
        if len(text) > 280:
            return PostResult(
                success=False,
                error=f"Tweet too long ({len(text)} chars). Max 280 characters."
            )
        
        self._tweet_counter += 1
        tweet_id = str(self._tweet_counter)
        
        self._mock_tweets.append({
            'id': tweet_id,
            'text': text,
            'created_at': datetime.utcnow().isoformat(),
            **kwargs
        })
        
        return PostResult(
            success=True,
            tweet_id=tweet_id,
            tweet_url=f"https://twitter.com/i/web/status/{tweet_id}",
            data={'id': tweet_id, 'text': text}
        )
    
    def get_mock_tweets(self) -> List[Dict]:
        """Get all mock tweets posted."""
        return self._mock_tweets.copy()
    
    def clear_mock_tweets(self):
        """Clear mock tweet history."""
        self._mock_tweets = []
