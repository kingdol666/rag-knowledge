"""
Pydantic models for API request/response.
"""
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Service status")


class ParseResponse(BaseModel):
    success: bool = Field(..., description="Whether parsing succeeded")
    data: Optional[dict] = Field(default=None, description="Response payload")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class MineruParseResult(BaseModel):
    """Structured result from MinerU PDF parse 鈥?output paths + metadata."""
    success: bool = Field(..., description="Whether parsing succeeded")
    output_dir: str = Field(default="", description="Absolute path to the output directory")
    markdown_path: Optional[str] = Field(default=None, description="Path to the extracted .md file")
    markdown: Optional[str] = Field(default=None, description="Extracted markdown content (the full text)")
    images_dir: Optional[str] = Field(default=None, description="Path to the extracted images directory")
    source_filename: str = Field(default="", description="Original uploaded filename")
    image_count: int = Field(default=0, description="Number of extracted images")
    has_markdown: bool = Field(default=False, description="Whether markdown content was extracted")
    metadata: dict = Field(default_factory=dict, description="Full parsing metadata from MinerU")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class AgentExecuteRequest(BaseModel):
    input_text: str = Field(..., description="User input for the agent")
    context: Optional[dict] = Field(default=None, description="Optional runtime context")
    thread_id: Optional[str] = Field(default=None, description="Conversation thread ID")
    include_messages: bool = Field(default=True, description="Include message history")


class AgentExecuteResponse(BaseModel):
    success: bool = Field(..., description="Whether parsing succeeded")
    result: Optional[dict] = Field(default=None, description="Agent output")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class HealthResponseOld(BaseModel):
    """Backward-compatible health check for the frontend proxy."""
    status: str = Field(default="healthy")
    version: str = Field(default="1.0.0")

