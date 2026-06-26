from typing import Annotated, List

from pydantic import BaseModel, Field


class NameSchema(BaseModel):
    name: Annotated[str, Field(..., description="name")]
    reference: Annotated[str, Field(..., description="reference")]
    moral: Annotated[str, Field(..., description="moral")]
    domain: str = Field(default="", description="suggested .com domain for company names")
    domain_status: str = Field(default="", description="domain availability status")


class NameResultSchema(BaseModel):
    names: List[NameSchema]
