"""
Settings API Endpoints
Handles cloud service configuration from admin dashboard.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger(__name__)

# Import settings service
try:
    from backend.services.settings_service import settings_service
except:
    from services.settings_service import settings_service


class ServiceSettings(BaseModel):
    """Model for service settings update"""
    settings: Dict[str, str]


@router.get("/all")
async def get_all_settings():
    """Get all service settings (masked)"""
    try:
        settings = settings_service.get_all_settings()
        return {
            "success": True,
            "settings": settings
        }
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{service}")
async def get_service_settings(service: str):
    """Get settings for a specific service"""
    try:
        settings = settings_service.get_service_settings(service)
        if not settings:
            raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
        
        return {
            "success": True,
            "service": service,
            "settings": settings
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting {service} settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{service}")
async def update_service_settings(service: str, data: ServiceSettings):
    """Update settings for a specific service"""
    try:
        success = settings_service.update_service_settings(service, data.settings)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to update {service} settings")
        
        return {
            "success": True,
            "message": f"Settings updated for {service}",
            "service": service
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating {service} settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{service}/test")
async def test_service_connection(service: str):
    """Test connection to a cloud service"""
    try:
        result = settings_service.test_connection(service)
        
        return {
            "success": result.get('success', False),
            "message": result.get('message', 'Unknown error'),
            "details": result.get('details', {}),
            "service": service
        }
    except Exception as e:
        logger.error(f"Error testing {service} connection: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "service": service
        }


@router.post("/reload")
async def reload_settings():
    """Reload settings from .env file"""
    try:
        settings_service.load_settings()
        return {
            "success": True,
            "message": "Settings reloaded successfully"
        }
    except Exception as e:
        logger.error(f"Error reloading settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/all")
async def get_all_service_status():
    """Get connection status for all services"""
    try:
        services = ['supabase', 'upstash', 'cloudflare_r2', 'openrouter', 'mappls', 'pinecone', 'apify']
        status = {}
        
        for service in services:
            result = settings_service.test_connection(service)
            status[service] = {
                'connected': result.get('success', False),
                'message': result.get('message', ''),
                'details': result.get('details', {})
            }
        
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        logger.error(f"Error getting service status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
