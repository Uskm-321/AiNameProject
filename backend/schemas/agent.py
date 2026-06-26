from typing import Annotated, List

from pydantic import BaseModel, Field


class DomainSchema(BaseModel):
    domain: str = Field(default="", description="checked .com domain")
    available: bool | None = Field(default=None, description="whether the domain is available")
    status: str = Field(default="unknown", description="available/taken/timeout/error/unsupported")
    message: str = Field(default="", description="human-readable domain check result")


class NameSchema(BaseModel):
    name: Annotated[str, Field(..., description="name")]
    reference: Annotated[str, Field(..., description="reference")]
    moral: Annotated[str, Field(..., description="moral")]
    style_reason: str = Field(default="", description="why this name matches the selected style")
    score: int = Field(default=0, ge=0, le=100, description="recommendation score")
    domain: str = Field(default="", description="suggested .com domain for company names")
    domain_status: str = Field(default="", description="domain availability status")
    domains: List[DomainSchema] = Field(default_factory=list, description="checked .com domain candidates")


class NameResultSchema(BaseModel):
    names: List[NameSchema]
