"""
Data connectors for loading real estate data from various sources.
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class DataConnector(ABC):
    """Abstract base class for data connectors."""
    
    @abstractmethod
    def load_data(self, **kwargs) -> pd.DataFrame:
        """Load data from the source."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test connection to the data source."""
        pass


class CSVConnector(DataConnector):
    """Load data from CSV files."""
    
    def __init__(self, file_path: str):
        """Initialize with path to CSV file."""
        self.file_path = Path(file_path)
    
    def load_data(self, **kwargs) -> pd.DataFrame:
        """Load data from CSV file."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")
        
        return pd.read_csv(self.file_path, **kwargs)
    
    def test_connection(self) -> bool:
        """Test if CSV file exists and is readable."""
        return self.file_path.exists() and os.access(self.file_path, os.R_OK)


class APIBaseConnector(DataConnector):
    """Base class for API-based connectors."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize with API base URL and optional API key."""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def _make_request(
        self,
        endpoint: str,
        method: str = 'GET',
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an API request with error handling."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Add API key to headers if provided
        headers = headers or {}
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                data=data,
                json=json_data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test connection to the API."""
        try:
            response = self.session.head(self.base_url, timeout=10)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


class RealEstateAPI(APIBaseConnector):
    """Connector for a generic real estate API."""
    
    def load_data(
        self,
        location: str,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_bedrooms: Optional[int] = None,
        **kwargs
    ) -> pd.DataFrame:
        """Load real estate listings."""
        params = {
            'location': location,
            'property_type': property_type,
            'min_price': min_price,
            'max_price': max_price,
            'min_bedrooms': min_bedrooms,
            **kwargs
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        # Make API request
        response = self._make_request('listings', params=params)
        
        # Convert to DataFrame
        if 'listings' in response:
            return pd.DataFrame(response['listings'])
        return pd.DataFrame()


class DataLoader:
    """Unified interface for loading data from multiple sources."""
    
    @staticmethod
    def from_csv(file_path: str, **kwargs) -> pd.DataFrame:
        """Load data from a CSV file."""
        connector = CSVConnector(file_path)
        return connector.load_data(**kwargs)
    
    @staticmethod
    def from_api(
        base_url: str,
        endpoint: str,
        api_key: Optional[str] = None,
        method: str = 'GET',
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """Load data from a generic API endpoint."""
        connector = APIBaseConnector(base_url, api_key)
        response = connector._make_request(
            endpoint=endpoint,
            method=method,
            params=params,
            headers=headers,
            data=data,
            json_data=json_data
        )
        
        # Convert response to DataFrame
        if isinstance(response, dict):
            if 'data' in response:
                return pd.DataFrame(response['data'])
            return pd.DataFrame([response])
        elif isinstance(response, list):
            return pd.DataFrame(response)
        else:
            raise ValueError("Unsupported API response format")
