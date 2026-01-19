"""
Pydantic models for request and response objects
"""
from typing import Optional
from pydantic import BaseModel, Field
from src.config.settings import DEFAULT_BUCKET, DEFAULT_REGION

class PDFRequest(BaseModel):
    bucket: Optional[str] = Field(default=DEFAULT_BUCKET)
    file_key: Optional[str] = None
    region: Optional[str] = Field(default=DEFAULT_REGION)
    raw_html: Optional[str] = None
    url: Optional[str] = None
    header_template: Optional[str] = None
    footer_template: Optional[str] = None
    pdf_format: Optional[str] = Field(default="Letter")
    scale: Optional[float] = Field(default=0.9)
    margin: Optional[dict] = Field(default=None)


class PDFResponse(BaseModel):
    url: Optional[str] = None 