"""
Data Quality Service - Monitors and reports on data quality
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4
from enum import Enum

logger = logging.getLogger(__name__)


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueType(str, Enum):
    MISSING_FIELD = "missing_field"
    INVALID_FORMAT = "invalid_format"
    OUT_OF_RANGE = "out_of_range"
    DUPLICATE = "duplicate"
    INCONSISTENT = "inconsistent"
    SCHEMA_MISMATCH = "schema_mismatch"


class IssueStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class DataQualityService:
    """Monitors and reports on data quality across all sources"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._issues: Dict[str, dict] = {}
        self._quality_scores: Dict[str, float] = {}
    
    async def log_issue(
        self,
        source_id: str,
        issue_type: str,
        severity: str,
        field_name: str = None,
        expected_value: str = None,
        actual_value: str = None,
        message: str = None,
        record_id: str = None,
        job_id: str = None
    ) -> dict:
        """Log a data quality issue"""
        issue = {
            'id': str(uuid4()),
            'source_id': source_id,
            'job_id': job_id,
            'record_id': record_id,
            'issue_type': issue_type,
            'severity': severity,
            'field_name': field_name,
            'expected_value': expected_value,
            'actual_value': actual_value,
            'message': message,
            'status': IssueStatus.OPEN.value,
            'created_at': datetime.utcnow().isoformat(),
            'resolved_at': None,
            'resolved_by': None,
            'resolution_note': None
        }
        
        self._issues[issue['id']] = issue
        logger.warning(f"Data quality issue: {issue_type} - {message}")
        return issue
    
    async def resolve_issue(
        self,
        issue_id: str,
        resolved_by: str = None,
        resolution_note: str = None
    ) -> Optional[dict]:
        """Mark an issue as resolved"""
        issue = self._issues.get(issue_id)
        if not issue:
            return None
        
        issue['status'] = IssueStatus.RESOLVED.value
        issue['resolved_at'] = datetime.utcnow().isoformat()
        issue['resolved_by'] = resolved_by
        issue['resolution_note'] = resolution_note
        
        logger.info(f"Resolved issue: {issue_id}")
        return issue
    
    async def ignore_issue(
        self,
        issue_id: str,
        ignored_by: str = None,
        reason: str = None
    ) -> Optional[dict]:
        """Mark an issue as ignored"""
        issue = self._issues.get(issue_id)
        if not issue:
            return None
        
        issue['status'] = IssueStatus.IGNORED.value
        issue['resolved_at'] = datetime.utcnow().isoformat()
        issue['resolved_by'] = ignored_by
        issue['resolution_note'] = reason
        
        logger.info(f"Ignored issue: {issue_id}")
        return issue
    
    async def get_issues(
        self,
        source_id: str = None,
        status: str = None,
        severity: str = None,
        issue_type: str = None,
        limit: int = 100
    ) -> List[dict]:
        """Get issues with optional filters"""
        issues = list(self._issues.values())
        
        if source_id:
            issues = [i for i in issues if i['source_id'] == source_id]
        if status:
            issues = [i for i in issues if i['status'] == status]
        if severity:
            issues = [i for i in issues if i['severity'] == severity]
        if issue_type:
            issues = [i for i in issues if i['issue_type'] == issue_type]
        
        # Sort by created_at desc
        issues.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Add mock issues for demo
        if not issues:
            issues = self._get_mock_issues(source_id, status, severity)
        
        return issues[:limit]
    
    async def get_issue(self, issue_id: str) -> Optional[dict]:
        """Get a specific issue"""
        return self._issues.get(issue_id)
    
    async def calculate_quality_score(self, source_id: str) -> float:
        """Calculate quality score for a source (0-1)"""
        issues = await self.get_issues(source_id=source_id, status='open')
        
        if not issues:
            return 1.0
        
        # Weight by severity
        weights = {'error': 0.1, 'warning': 0.02, 'info': 0.005}
        penalty = sum(weights.get(i['severity'], 0.01) for i in issues)
        
        score = max(0.0, 1.0 - penalty)
        self._quality_scores[source_id] = score
        
        return score
    
    async def get_quality_summary(self, source_id: str = None) -> dict:
        """Get quality summary across sources"""
        issues = await self.get_issues(source_id=source_id)
        
        summary = {
            'total_issues': len(issues),
            'open_issues': sum(1 for i in issues if i['status'] == 'open'),
            'resolved_issues': sum(1 for i in issues if i['status'] == 'resolved'),
            'ignored_issues': sum(1 for i in issues if i['status'] == 'ignored'),
            'by_severity': {
                'error': sum(1 for i in issues if i['severity'] == 'error'),
                'warning': sum(1 for i in issues if i['severity'] == 'warning'),
                'info': sum(1 for i in issues if i['severity'] == 'info')
            },
            'by_type': {},
            'recent_issues': issues[:10]
        }
        
        # Count by type
        for issue in issues:
            itype = issue['issue_type']
            summary['by_type'][itype] = summary['by_type'].get(itype, 0) + 1
        
        return summary
    
    async def get_metrics(self, time_range: str = '7d') -> dict:
        """Get quality metrics over time"""
        now = datetime.utcnow()
        
        # Parse time range
        if time_range == '24h':
            start_time = now - timedelta(hours=24)
        elif time_range == '7d':
            start_time = now - timedelta(days=7)
        elif time_range == '30d':
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=7)
        
        issues = await self.get_issues()
        
        # Filter by time
        recent_issues = [
            i for i in issues 
            if datetime.fromisoformat(i['created_at']) >= start_time
        ]
        
        # Calculate trend
        total_recent = len(recent_issues)
        resolved_recent = sum(1 for i in recent_issues if i['status'] == 'resolved')
        
        return {
            'time_range': time_range,
            'issues_created': total_recent,
            'issues_resolved': resolved_recent,
            'resolution_rate': resolved_recent / max(total_recent, 1),
            'avg_resolution_time_hours': 4.5,  # Mock value
            'quality_trend': 'improving',  # Mock value
            'top_issue_types': [
                {'type': 'missing_field', 'count': 15},
                {'type': 'invalid_format', 'count': 8},
                {'type': 'out_of_range', 'count': 5}
            ]
        }
    
    def _get_mock_issues(
        self,
        source_id: str = None,
        status: str = None,
        severity: str = None
    ) -> List[dict]:
        """Return mock issues for demo"""
        now = datetime.utcnow()
        issues = [
            {
                'id': 'issue-001',
                'source_id': 'src-001',
                'source_name': 'MagicBricks Scraper',
                'issue_type': 'missing_field',
                'severity': 'warning',
                'field_name': 'pincode',
                'message': 'Missing pincode for 15 properties in Whitefield area',
                'status': 'open',
                'created_at': (now - timedelta(hours=2)).isoformat()
            },
            {
                'id': 'issue-002',
                'source_id': 'src-002',
                'source_name': '99acres Scraper',
                'issue_type': 'out_of_range',
                'severity': 'error',
                'field_name': 'price',
                'expected_value': '1L - 50Cr',
                'actual_value': '0',
                'message': '3 properties have zero price value',
                'status': 'open',
                'created_at': (now - timedelta(hours=4)).isoformat()
            },
            {
                'id': 'issue-003',
                'source_id': 'src-006',
                'source_name': 'Registry Transactions',
                'issue_type': 'duplicate',
                'severity': 'warning',
                'message': '12 duplicate transaction records detected',
                'status': 'open',
                'created_at': (now - timedelta(days=1)).isoformat()
            },
            {
                'id': 'issue-004',
                'source_id': 'src-001',
                'source_name': 'MagicBricks Scraper',
                'issue_type': 'invalid_format',
                'severity': 'info',
                'field_name': 'area_sqft',
                'message': 'Area format inconsistency: some values in sqm',
                'status': 'resolved',
                'created_at': (now - timedelta(days=2)).isoformat(),
                'resolved_at': (now - timedelta(days=1)).isoformat(),
                'resolution_note': 'Added unit conversion in ETL pipeline'
            },
            {
                'id': 'issue-005',
                'source_id': 'src-002',
                'source_name': '99acres Scraper',
                'issue_type': 'schema_mismatch',
                'severity': 'error',
                'message': 'New field "possession_date" not in schema',
                'status': 'open',
                'created_at': (now - timedelta(hours=6)).isoformat()
            },
            {
                'id': 'issue-006',
                'source_id': 'src-007',
                'source_name': 'Real-time Price Stream',
                'issue_type': 'inconsistent',
                'severity': 'warning',
                'field_name': 'price_per_sqft',
                'message': 'Price per sqft differs >20% from calculated value',
                'status': 'open',
                'created_at': (now - timedelta(minutes=45)).isoformat()
            }
        ]
        
        if source_id:
            issues = [i for i in issues if i['source_id'] == source_id]
        if status:
            issues = [i for i in issues if i['status'] == status]
        if severity:
            issues = [i for i in issues if i['severity'] == severity]
        
        return issues


# Singleton instance
data_quality_service = DataQualityService()
