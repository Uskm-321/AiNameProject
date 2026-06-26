# 限制用户输入数据和接口返回数据的格式
from pydantic import BaseModel, Field, model_validator
from typing import Annotated, Literal, List
from .agent import NameSchema


# 接收用户数据的改造，可以给多种场景起名
CategoryLiteral = Literal["人名", "企业名", "宠物名"]

class NameIn(BaseModel):
    category: Annotated[CategoryLiteral, Field("人名", description="Name category")]
    surname: Annotated[str, Field("", description="姓氏")]
    gender: Annotated[Literal["不限", "男", "女"], Field("不限", description="性别")]
    length: Annotated[Literal["不限", "单字", "两字"], Field("不限", description="字数")]
    other: Annotated[str | None, Field("", description="其他要求")]
    exclude: Annotated[List[str], Field([], description="排除的名字")]

    # 如果给人起名字，需要给一个姓
    @model_validator(mode="after")
    def validate_firstname(self):
        if self.category == "人名" and not self.surname:
            raise ValueError("生成姓名时，姓氏不能为空！")
        return self


class NameOut(BaseModel):
    names: List[NameSchema]


class FeedbackIn(BaseModel):
    thread_id:str = Annotated[str, Field(...,description="访问窗口")]
    category:Annotated[CategoryLiteral,Field("企业名",description="Name category")]
    feedback:str = Annotated[str, Field(...,description="微调的方向")]


class NameWithThreadOut(BaseModel):
    thread_id:str
    names:List[NameSchema]