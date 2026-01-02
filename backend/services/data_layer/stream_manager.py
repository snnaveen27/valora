"""
Stream Manager - Manages real-time data streaming
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from uuid import uuid4
from enum import Enum

logger = logging.getLogger(__name__)


class StreamType(str, Enum):
    WEBSOCKET = "websocket"
    KAFKA = "kafka"
    WEBHOOK = "webhook"
    SSE = "sse"
    POLLING = "polling"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class StreamManager:
    """Manages real-time data streams"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._subscriptions: Dict[str, dict] = {}
        self._handlers: Dict[str, Callable] = {}
    
    async def create_subscription(
        self,
        source_id: str,
        stream_type: str,
        endpoint_url: str,
        config: dict = None
    ) -> dict:
        """Create a new stream subscription"""
        subscription = {
            'id': str(uuid4()),
            'source_id': source_id,
            'stream_type': stream_type,
            'endpoint_url': endpoint_url,
            'status': 'active',
            'connection_status': ConnectionStatus.DISCONNECTED.value,
            'messages_received': 0,
            'messages_processed': 0,
            'messages_failed': 0,
            'avg_latency_ms': 0,
            'buffer_size': config.get('buffer_size', 1000) if config else 1000,
            'current_buffer_usage': 0,
            'auto_reconnect': True,
            'reconnect_attempts': 0,
            'max_reconnect_attempts': 10,
            'last_message_at': None,
            'created_at': datetime.utcnow().isoformat(),
            'config': config or {}
        }
        
        self._subscriptions[subscription['id']] = subscription
        logger.info(f"Created stream subscription: {subscription['id']}")
        return subscription
    
    async def connect(self, subscription_id: str) -> dict:
        """Connect to a stream"""
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        sub['connection_status'] = ConnectionStatus.CONNECTED.value
        sub['reconnect_attempts'] = 0
        
        logger.info(f"Connected to stream: {subscription_id}")
        return sub
    
    async def disconnect(self, subscription_id: str) -> dict:
        """Disconnect from a stream"""
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        sub['connection_status'] = ConnectionStatus.DISCONNECTED.value
        
        logger.info(f"Disconnected from stream: {subscription_id}")
        return sub
    
    async def pause(self, subscription_id: str) -> dict:
        """Pause a stream subscription"""
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        sub['status'] = 'paused'
        await self.disconnect(subscription_id)
        
        logger.info(f"Paused stream: {subscription_id}")
        return sub
    
    async def resume(self, subscription_id: str) -> dict:
        """Resume a paused stream"""
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        sub['status'] = 'active'
        await self.connect(subscription_id)
        
        logger.info(f"Resumed stream: {subscription_id}")
        return sub
    
    async def record_message(
        self,
        subscription_id: str,
        success: bool = True,
        latency_ms: int = 0
    ) -> None:
        """Record a message receipt"""
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            return
        
        sub['messages_received'] += 1
        sub['last_message_at'] = datetime.utcnow().isoformat()
        
        if success:
            sub['messages_processed'] += 1
        else:
            sub['messages_failed'] += 1
        
        # Update rolling average latency
        if latency_ms > 0:
            current_avg = sub['avg_latency_ms']
            total = sub['messages_received']
            sub['avg_latency_ms'] = int((current_avg * (total - 1) + latency_ms) / total)
    
    async def get_subscription(self, subscription_id: str) -> Optional[dict]:
        """Get subscription details"""
        return self._subscriptions.get(subscription_id)
    
    async def get_subscriptions(self, source_id: str = None, status: str = None) -> List[dict]:
        """Get subscriptions with optional filters"""
        subs = list(self._subscriptions.values())
        
        if source_id:
            subs = [s for s in subs if s['source_id'] == source_id]
        if status:
            subs = [s for s in subs if s['status'] == status]
        
        # Add mock subscriptions for demo
        if not subs:
            subs = self._get_mock_subscriptions(source_id, status)
        
        return subs
    
    async def get_metrics(self, subscription_id: str = None) -> dict:
        """Get stream metrics"""
        if subscription_id:
            sub = self._subscriptions.get(subscription_id)
            if not sub:
                return {}
            return {
                'subscription_id': subscription_id,
                'messages_received': sub['messages_received'],
                'messages_processed': sub['messages_processed'],
                'messages_failed': sub['messages_failed'],
                'success_rate': sub['messages_processed'] / max(sub['messages_received'], 1),
                'avg_latency_ms': sub['avg_latency_ms'],
                'buffer_usage_percent': sub['current_buffer_usage'] / sub['buffer_size'] * 100
            }
        
        # Aggregate metrics
        total_received = sum(s['messages_received'] for s in self._subscriptions.values())
        total_processed = sum(s['messages_processed'] for s in self._subscriptions.values())
        total_failed = sum(s['messages_failed'] for s in self._subscriptions.values())
        
        return {
            'total_subscriptions': len(self._subscriptions),
            'active_connections': sum(1 for s in self._subscriptions.values() if s['connection_status'] == ConnectionStatus.CONNECTED.value),
            'total_received': total_received,
            'total_processed': total_processed,
            'total_failed': total_failed,
            'overall_success_rate': total_processed / max(total_received, 1)
        }
    
    async def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription"""
        if subscription_id in self._subscriptions:
            await self.disconnect(subscription_id)
            del self._subscriptions[subscription_id]
            logger.info(f"Deleted subscription: {subscription_id}")
            return True
        return False
    
    def _get_mock_subscriptions(self, source_id: str = None, status: str = None) -> List[dict]:
        """Return mock subscriptions for demo"""
        now = datetime.utcnow()
        subs = [
            {
                'id': 'stream-001',
                'source_id': 'src-007',
                'stream_type': 'websocket',
                'endpoint_url': 'wss://stream.valora.ai/prices',
                'status': 'active',
                'connection_status': 'connected',
                'messages_received': 156780,
                'messages_processed': 155890,
                'messages_failed': 890,
                'avg_latency_ms': 45,
                'buffer_size': 1000,
                'current_buffer_usage': 23,
                'last_message_at': now.isoformat()
            },
            {
                'id': 'stream-002',
                'source_id': 'src-005',
                'stream_type': 'webhook',
                'endpoint_url': 'https://api.mappls.com/webhooks/pois',
                'status': 'active',
                'connection_status': 'connected',
                'messages_received': 8920,
                'messages_processed': 8915,
                'messages_failed': 5,
                'avg_latency_ms': 120,
                'buffer_size': 500,
                'current_buffer_usage': 0,
                'last_message_at': (now - timedelta(minutes=15)).isoformat()
            }
        ]
        
        if source_id:
            subs = [s for s in subs if s['source_id'] == source_id]
        if status:
            subs = [s for s in subs if s['status'] == status]
        
        return subs


# Singleton instance
stream_manager = StreamManager()
