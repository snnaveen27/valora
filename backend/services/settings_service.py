"""
Settings Management Service
Handles cloud service credentials and configuration from admin dashboard.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import set_key, load_dotenv
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

logger = logging.getLogger(__name__)

class SettingsService:
    """Manages application settings and cloud service credentials"""
    
    def __init__(self):
        self.env_file = Path(".env")
        self.settings_cache = {}
        self.load_settings()
    
    def load_settings(self):
        """Load current settings from .env"""
        load_dotenv(override=True)

        def _clean_env_value(value: str) -> str:
            if not value:
                return value
            v = value.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                v = v[1:-1]
            return v.strip()

        def _ensure_sslmode_require(db_url: str) -> str:
            try:
                parsed = urlparse(db_url)
                host = (parsed.hostname or "").lower()
                if "supabase" not in host:
                    return db_url
                query = dict(parse_qsl(parsed.query, keep_blank_values=True))
                if not query.get("sslmode"):
                    query["sslmode"] = "require"
                    parsed = parsed._replace(query=urlencode(query))
                    return urlunparse(parsed)
                return db_url
            except Exception:
                return db_url

        database_url = os.getenv('DATABASE_URL_POOLER') or os.getenv('DATABASE_URL', '')
        database_url = _ensure_sslmode_require(_clean_env_value(database_url))
        
        self.settings_cache = {
            'supabase': {
                'url': os.getenv('SUPABASE_URL', ''),
                'anon_key': os.getenv('SUPABASE_ANON_KEY', ''),
                'service_key': os.getenv('SUPABASE_SERVICE_KEY', ''),
                'database_url': database_url,
            },
            'upstash': {
                'redis_url': os.getenv('REDIS_URL', ''),
                'rest_url': os.getenv('UPSTASH_REDIS_REST_URL', ''),
                'rest_token': os.getenv('UPSTASH_REDIS_REST_TOKEN', ''),
            },
            'cloudflare_r2': {
                'account_id': os.getenv('R2_ACCOUNT_ID', ''),
                'access_key_id': os.getenv('R2_ACCESS_KEY_ID', ''),
                'secret_access_key': os.getenv('R2_SECRET_ACCESS_KEY', ''),
                'bucket_name': os.getenv('R2_BUCKET_NAME', 'valora-storage'),
                'endpoint': os.getenv('R2_ENDPOINT', ''),
            },
            'openrouter': {
                'api_key': os.getenv('OPENROUTER_API_KEY', ''),
                'model': os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3-haiku'),
            },
            'mappls': {
                'api_key': os.getenv('MAPPLS_API_KEY', ''),
                'vite_api_key': os.getenv('VITE_MAPPLS_API_KEY', ''),
            },
            'pinecone': {
                'api_key': os.getenv('PINECONE_API_KEY', ''),
                'environment': os.getenv('PINECONE_ENVIRONMENT', 'us-west1-gcp-free'),
                'index': os.getenv('PINECONE_INDEX', 'valora-realestate'),
            },
            'apify': {
                'api_token': os.getenv('APIFY_API_TOKEN', ''),
            }
        }
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings (with sensitive data masked for display)"""
        masked_settings = {}
        for service, config in self.settings_cache.items():
            masked_settings[service] = {}
            for key, value in config.items():
                if value and any(word in key.lower() for word in ['key', 'token', 'password', 'secret']):
                    # Mask sensitive data
                    if len(value) > 8:
                        masked_settings[service][key] = value[:4] + '*' * (len(value) - 8) + value[-4:]
                    else:
                        masked_settings[service][key] = '*' * len(value)
                else:
                    masked_settings[service][key] = value
        return masked_settings
    
    def get_service_settings(self, service: str) -> Dict[str, str]:
        """Get settings for a specific service"""
        return self.settings_cache.get(service, {})
    
    def update_service_settings(self, service: str, settings: Dict[str, str]) -> bool:
        """Update settings for a specific service"""
        try:
            if service not in self.settings_cache:
                return False
            
            # Update cache
            self.settings_cache[service].update(settings)
            
            # Update .env file
            env_mapping = self._get_env_mapping(service)
            
            for setting_key, env_key in env_mapping.items():
                if setting_key in settings:
                    value = settings[setting_key]
                    self._update_env_var(env_key, value)

                    # Keep backward compatibility: if Supabase DB URL is updated, mirror it into DATABASE_URL
                    if service == 'supabase' and setting_key == 'database_url' and env_key == 'DATABASE_URL_POOLER':
                        self._update_env_var('DATABASE_URL', value)
            
            logger.info(f"Updated settings for {service}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating settings for {service}: {str(e)}")
            return False
    
    def _get_env_mapping(self, service: str) -> Dict[str, str]:
        """Map service settings to .env variable names"""
        mappings = {
            'supabase': {
                'url': 'SUPABASE_URL',
                'anon_key': 'SUPABASE_ANON_KEY',
                'service_key': 'SUPABASE_SERVICE_KEY',
                # Prefer pooler URL for reliability (port 6543)
                'database_url': 'DATABASE_URL_POOLER',
            },
            'upstash': {
                'redis_url': 'REDIS_URL',
                'rest_url': 'UPSTASH_REDIS_REST_URL',
                'rest_token': 'UPSTASH_REDIS_REST_TOKEN',
            },
            'cloudflare_r2': {
                'account_id': 'R2_ACCOUNT_ID',
                'access_key_id': 'R2_ACCESS_KEY_ID',
                'secret_access_key': 'R2_SECRET_ACCESS_KEY',
                'bucket_name': 'R2_BUCKET_NAME',
                'endpoint': 'R2_ENDPOINT',
            },
            'openrouter': {
                'api_key': 'OPENROUTER_API_KEY',
                'model': 'OPENROUTER_MODEL',
            },
            'mappls': {
                'api_key': 'MAPPLS_API_KEY',
                'vite_api_key': 'VITE_MAPPLS_API_KEY',
            },
            'pinecone': {
                'api_key': 'PINECONE_API_KEY',
                'environment': 'PINECONE_ENVIRONMENT',
                'index': 'PINECONE_INDEX',
            },
            'apify': {
                'api_token': 'APIFY_API_TOKEN',
            }
        }
        return mappings.get(service, {})
    
    def _update_env_var(self, key: str, value: str):
        """Update a single environment variable in .env file"""
        try:
            if not self.env_file.exists():
                self.env_file.touch()
            
            set_key(str(self.env_file), key, value)
            os.environ[key] = value
            
        except Exception as e:
            logger.error(f"Error updating .env variable {key}: {str(e)}")
    
    def test_connection(self, service: str) -> Dict[str, Any]:
        """Test connection to a cloud service"""
        try:
            if service == 'supabase':
                return self._test_supabase()
            elif service == 'upstash':
                return self._test_upstash()
            elif service == 'cloudflare_r2':
                return self._test_r2()
            elif service == 'openrouter':
                return self._test_openrouter()
            elif service == 'mappls':
                return self._test_mappls()
            elif service == 'pinecone':
                return self._test_pinecone()
            elif service == 'apify':
                return self._test_apify()
            else:
                return {'success': False, 'message': 'Unknown service'}
                
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _test_supabase(self) -> Dict[str, Any]:
        """Test Supabase connection"""
        try:
            from sqlalchemy import create_engine, text

            db_url = self.settings_cache['supabase']['database_url']
            if not db_url or '[PROJECT-REF]' in db_url or '[YOUR_SUPABASE_PASSWORD]' in db_url:
                return {'success': False, 'message': 'Database URL not configured'}

            parsed_for_validation = urlparse(db_url)
            host_for_validation = (parsed_for_validation.hostname or '').lower()
            if host_for_validation.startswith('db.') and host_for_validation.endswith('.supabase.co'):
                return {
                    'success': False,
                    'message': 'Use Supabase Connection Pooling URL (pooler) instead of db.<ref>.supabase.co',
                    'details': {
                        'expected_format': 'postgresql://postgres.<PROJECT-REF>:<PASSWORD>@aws-0-<REGION>.pooler.supabase.com:6543/postgres'
                    }
                }

            parsed = urlparse(db_url)
            host = (parsed.hostname or "").lower()
            connect_args = {'connect_timeout': 5}
            if 'supabase' in host:
                connect_args['sslmode'] = 'require'

            engine = create_engine(db_url, connect_args=connect_args)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                return {
                    'success': True, 
                    'message': 'Connected successfully',
                    'details': {'version': version.split(',')[0]}
                }
        except Exception as e:
            return {'success': False, 'message': f'Connection failed: {str(e)[:100]}'}
    
    def _test_upstash(self) -> Dict[str, Any]:
        """Test Upstash Redis connection"""
        try:
            from redis import Redis
            
            redis_url = self.settings_cache['upstash']['redis_url']
            if not redis_url or '[YOUR_UPSTASH_PASSWORD]' in redis_url:
                return {'success': False, 'message': 'Redis URL not configured'}
            
            client = Redis.from_url(redis_url, socket_connect_timeout=5, socket_timeout=5)
            client.ping()
            info = client.info()
            
            return {
                'success': True,
                'message': 'Connected successfully',
                'details': {
                    'version': info.get('redis_version', 'Unknown'),
                    'memory': info.get('used_memory_human', 'Unknown')
                }
            }
        except Exception as e:
            return {'success': False, 'message': f'Connection failed: {str(e)[:100]}'}
    
    def _test_r2(self) -> Dict[str, Any]:
        """Test Cloudflare R2 connection"""
        try:
            import boto3
            
            config = self.settings_cache['cloudflare_r2']
            if not all([config['endpoint'], config['access_key_id'], config['secret_access_key']]):
                return {'success': False, 'message': 'R2 credentials not configured'}
            
            s3 = boto3.client(
                's3',
                endpoint_url=config['endpoint'],
                aws_access_key_id=config['access_key_id'],
                aws_secret_access_key=config['secret_access_key'],
                region_name='auto'
            )
            
            response = s3.list_buckets()
            buckets = [b['Name'] for b in response.get('Buckets', [])]
            
            return {
                'success': True,
                'message': 'Connected successfully',
                'details': {'buckets': buckets}
            }
        except Exception as e:
            return {'success': False, 'message': f'Connection failed: {str(e)[:100]}'}
    
    def _test_openrouter(self) -> Dict[str, Any]:
        """Test OpenRouter API"""
        try:
            import requests
            
            api_key = self.settings_cache['openrouter']['api_key']
            if not api_key or 'your' in api_key.lower():
                return {'success': False, 'message': 'API key not configured'}
            
            response = requests.get(
                'https://openrouter.ai/api/v1/models',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=5
            )
            
            if response.status_code == 200:
                models = response.json().get('data', [])
                return {
                    'success': True,
                    'message': 'API key valid',
                    'details': {'models_available': len(models)}
                }
            else:
                return {'success': False, 'message': f'API error: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'message': f'Connection failed: {str(e)[:100]}'}
    
    def _test_mappls(self) -> Dict[str, Any]:
        """Test Mappls API"""
        try:
            import requests
            
            api_key = self.settings_cache['mappls']['api_key']
            if not api_key or 'your' in api_key.lower():
                return {'success': False, 'message': 'API key not configured'}
            
            # Simple test - check if key format is valid
            if len(api_key) < 20:
                return {'success': False, 'message': 'Invalid API key format'}
            
            return {
                'success': True,
                'message': 'API key configured',
                'details': {'key_length': len(api_key)}
            }
        except Exception as e:
            return {'success': False, 'message': f'Validation failed: {str(e)[:100]}'}
    
    def _test_pinecone(self) -> Dict[str, Any]:
        """Test Pinecone connection"""
        try:
            api_key = self.settings_cache['pinecone']['api_key']
            if not api_key or 'your' in api_key.lower():
                return {'success': False, 'message': 'API key not configured'}
            
            # Simple validation
            if not api_key.startswith('pcsk_'):
                return {'success': False, 'message': 'Invalid API key format'}
            
            return {
                'success': True,
                'message': 'API key configured',
                'details': {'index': self.settings_cache['pinecone']['index']}
            }
        except Exception as e:
            return {'success': False, 'message': f'Validation failed: {str(e)[:100]}'}
    
    def _test_apify(self) -> Dict[str, Any]:
        """Test Apify API"""
        try:
            import requests
            
            api_token = self.settings_cache['apify']['api_token']
            if not api_token or 'your' in api_token.lower():
                return {'success': False, 'message': 'API token not configured'}
            
            response = requests.get(
                'https://api.apify.com/v2/user',
                headers={'Authorization': f'Bearer {api_token}'},
                timeout=5
            )
            
            if response.status_code == 200:
                user_data = response.json().get('data', {})
                return {
                    'success': True,
                    'message': 'Connected successfully',
                    'details': {'username': user_data.get('username', 'Unknown')}
                }
            else:
                return {'success': False, 'message': f'API error: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'message': f'Connection failed: {str(e)[:100]}'}


# Global settings service instance
settings_service = SettingsService()
