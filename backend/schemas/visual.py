from pydantic import BaseModel, Field


class VisualGenerateIn(BaseModel):
    name: str = Field(..., min_length=1, description="企业名")
    moral: str = Field(default="", description="企业名寓意")
    brand_tone: str = Field(default="", description="品牌调性")
    other: str = Field(default="", description="补充要求")


class LogoImageOut(BaseModel):
    url: str
    prompt: str


class VisualGenerateOut(BaseModel):
    name: str
    slogans: list[str]
    visual_keywords: list[str]
    color_palette: list[str]
    logo_images: list[LogoImageOut]
    design_note: str
