"""
Input Validation and Sanitization
Prevents injection attacks and ensures data integrity
"""
import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator, Field
from fastapi import HTTPException

# Forbidden patterns for prompt injection
FORBIDDEN_PATTERNS = [
    r'ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|commands?|prompts?)',
    r'system\s+prompt',
    r'you\s+are\s+now',
    r'override\s+(previous\s+)?instructions?',
    r'disregard\s+(everything|all)',
    r'forget\s+(everything|all|your\s+instructions?)',
    r'new\s+role\s*:?\s*you\s+are',
    r'act\s+as\s+(if\s+)?you\s+(are|were)',
    r'pretend\s+(to\s+be|you\s+are)',
    r'<\s*system\s*>',
    r'\{\s*system\s*\}',
    r'developer\s+mode',
    r'jailbreak',
    r'dan\s+mode',
]

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b.*?\b(FROM|INTO|TABLE|DATABASE)\b)',
    r'(\b(UNION|OR)\b.*?\b(SELECT|1\s*=\s*1)\b)',
    r'(;\s*--|/\*|\*/|\bxp_)',
    r'(\bWAITFOR\s+DELAY\b)',
]

# XSS patterns
XSS_PATTERNS = [
    r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
    r'javascript\s*:',
    r'on\w+\s*=\s*["\']',
    r'<iframe\b',
    r'<object\b',
    r'<embed\b',
]

class ValidationError(Exception):
    """Custom validation error"""
    pass

class Sanitizer:
    """Input sanitization utilities"""
    
    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """
        Sanitize user prompt to prevent injection attacks
        """
        if not prompt:
            return prompt
        
        original = prompt
        
        # Remove prompt injection attempts
        for pattern in FORBIDDEN_PATTERNS:
            prompt = re.sub(pattern, '[REMOVED]', prompt, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove potential code execution
        prompt = re.sub(r'```[\s\S]*?```', '[CODE_BLOCK]', prompt)  # Remove code blocks
        prompt = re.sub(r'`[^`]+`', '[CODE]', prompt)  # Remove inline code
        
        # Remove URLs that could be malicious
        prompt = re.sub(r'https?://\S+', '[URL]', prompt)
        
        # Log if changes were made
        if prompt != original:
            print(f"[SANITIZER] Prompt sanitized. Removed: {set(original.split()) - set(prompt.split())}")
        
        return prompt.strip()
    
    @staticmethod
    def sanitize_sql_input(value: str) -> str:
        """Sanitize SQL input parameters"""
        if not value:
            return value
        
        # Check for SQL injection
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError("Invalid characters in input")
        
        # Escape special characters
        value = value.replace("'", "''")  # SQL escape
        value = value.replace("\\", "\\\\")  # Backslash escape
        value = value.replace("\x00", "")  # Remove null bytes
        
        return value
    
    @staticmethod
    def sanitize_html(content: str) -> str:
        """Remove HTML tags and XSS attempts"""
        if not content:
            return content
        
        # Check for XSS patterns
        for pattern in XSS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                raise ValidationError("Potentially malicious content detected")
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        return content
    
    @staticmethod
    def validate_location_name(name: str) -> str:
        """Validate Bangalore locality name"""
        if not name:
            return name
        
        # Only allow alphanumeric, spaces, and common punctuation
        if not re.match(r'^[\w\s\-\.,]+$', name):
            raise ValidationError(f"Invalid location name: {name}")
        
        # Max length
        if len(name) > 100:
            raise ValidationError("Location name too long")
        
        return name.strip()
    
    @staticmethod
    def sanitize_json(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize JSON data"""
        if isinstance(data, dict):
            return {
                k: Sanitizer.sanitize_json(v) 
                for k, v in data.items()
                if not k.startswith('_')  # Remove private keys
            }
        elif isinstance(data, list):
            return [Sanitizer.sanitize_json(item) for item in data]
        elif isinstance(data, str):
            return Sanitizer.sanitize_html(data)
        else:
            return data

# Pydantic models for validation
class ChatMessageValidator(BaseModel):
    """Validate chat messages"""
    role: str = Field(..., pattern='^(user|assistant|system)$')
    content: str = Field(..., max_length=5000)
    
    @validator('content')
    def sanitize_content(cls, v):
        return Sanitizer.sanitize_prompt(v)

class ChatRequestValidator(BaseModel):
    """Validate chat request"""
    messages: List[ChatMessageValidator] = Field(..., max_items=50)
    context: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None
    
    @validator('context')
    def validate_context(cls, v):
        if v:
            # Remove sensitive keys
            forbidden_keys = ['password', 'secret', 'token', 'key', 'auth']
            for key in list(v.keys()):
                if any(fk in key.lower() for fk in forbidden_keys):
                    del v[key]
        return v
    
    @validator('bbox')
    def validate_bbox(cls, v):
        if v and len(v) != 4:
            raise ValueError("Bounding box must have 4 coordinates")
        return v

class LocationQueryValidator(BaseModel):
    """Validate location queries"""
    query: str = Field(..., min_length=1, max_length=200)
    
    @validator('query')
    def validate_query(cls, v):
        # Check for injection
        Sanitizer.sanitize_sql_input(v)
        return Sanitizer.sanitize_prompt(v)

# FastAPI dependency
async def validate_chat_request(request: ChatRequestValidator):
    """Dependency for chat endpoint validation"""
    return request
