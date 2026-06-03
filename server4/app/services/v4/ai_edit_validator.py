"""
AI Edit Validator

Validates AI-generated patch operations to ensure they are safe and well-formed.
Prevents malicious or malformed patch operations from being applied to slides.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Any, Literal, Optional


class PatchOperation(BaseModel):
    """Represents a single patch operation with validation."""
    
    op: Literal["replace", "insert", "remove", "move", "swap-image", "set-crop", "set-layout-variant"]
    path: str
    value: Optional[Any] = None
    from_path: Optional[str] = None
    from_: Optional[str] = Field(default=None, alias="from")

    @validator('path')
    def validate_path(cls, v):
        """Validate that the path is safe and within allowed prefixes."""
        if not v:
            raise ValueError('Path cannot be empty')
        
        # Prevent path traversal attacks
        if '..' in v or v.startswith('/') or v.startswith('\\'):
            raise ValueError('Unsafe path: path traversal detected')
        
        # Restrict to safe prefixes only
        allowed_prefixes = ['props_json', 'artifacts', 'props', 'style']
        if not any(v.startswith(p) for p in allowed_prefixes):
            raise ValueError(f'Path outside allowed prefixes: {v}')
        
        # Limit path length to prevent DoS
        if len(v) > 200:
            raise ValueError('Path too long')
        
        return v

    @validator('value')
    def validate_value(cls, v, values):
        """Validate value based on operation type and size."""
        if v is None:
            return v
        
        op = values.get('op')
        
        # Prevent huge values that could cause memory issues
        if isinstance(v, str):
            if len(v) > 10000:  # 10KB limit
                raise ValueError('Value too large (max 10KB)')
        
        # For replace operations, ensure value is JSON-serializable
        if op == 'replace':
            try:
                import json
                json.dumps(v)
            except (TypeError, ValueError) as e:
                raise ValueError(f'Value must be JSON-serializable: {e}')
        
        return v

    @validator('from_path')
    def validate_from_path(cls, v):
        """Validate from_path for move operations."""
        if v is None:
            return v
        
        # Apply same validation as path
        if '..' in v or v.startswith('/') or v.startswith('\\'):
            raise ValueError('Unsafe from_path: path traversal detected')
        
        allowed_prefixes = ['props_json', 'artifacts', 'props', 'style']
        if not any(v.startswith(p) for p in allowed_prefixes):
            raise ValueError(f'from_path outside allowed prefixes: {v}')
        
        if len(v) > 200:
            raise ValueError('from_path too long')
        
        return v


class AIPatchResponse(BaseModel):
    """Response from AI containing validated patch operations."""
    
    patch_ops: List[PatchOperation]
    explanation: str


def validate_ai_patch(patch_ops: List[dict]) -> List[PatchOperation]:
    """
    Validate AI-generated patch operations.
    
    Args:
        patch_ops: List of patch operation dictionaries from AI
        
    Returns:
        List of validated PatchOperation objects
        
    Raises:
        ValueError: If any patch operation is invalid
    """
    if not patch_ops:
        raise ValueError('No patch operations provided')
    
    # Limit number of operations to prevent DoS
    if len(patch_ops) > 50:
        raise ValueError('Too many patch operations (max 50)')
    
    validated = []
    for op in patch_ops:
        try:
            validated.append(PatchOperation(**op))
        except Exception as e:
            raise ValueError(f'Invalid patch operation: {e}')
    
    return validated


def validate_patch_structure(patch_op: dict) -> bool:
    """
    Quick validation of patch operation structure.
    
    Args:
        patch_op: Patch operation dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['op', 'path']
    if not all(field in patch_op for field in required_fields):
        return False
    
    valid_ops = ["replace", "insert", "remove", "move", "swap-image", "set-crop", "set-layout-variant"]
    if patch_op['op'] not in valid_ops:
        return False
    
    return True
