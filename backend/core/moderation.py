import json

from fastapi import HTTPException
from sqlalchemy.ext.asyncio.session import AsyncSession

from models.admin import ModerationDecision, ReviewStatus
from repository.user_repo import AdminRepository


class ModerationService:
    def __init__(self, session: AsyncSession):
        self.repository = AdminRepository(session=session)

    async def _find_matched_words(self, text: str) -> list[str]:
        if not text:
            return []
        rules = await self.repository.get_active_sensitive_words()
        lowered_text = text.lower()
        matched_words = []
        for rule in rules:
            if rule.word and rule.word.lower() in lowered_text:
                matched_words.append(rule.word)
        return matched_words

    async def ensure_request_allowed(self, user_id: int, source: str, input_text: str):
        matched_words = await self._find_matched_words(input_text)
        if not matched_words:
            await self.repository.create_moderation_record(
                user_id=user_id,
                source=source,
                input_text=input_text,
                output_text=None,
                matched_words=None,
                decision=ModerationDecision.PASS.value,
                review_status=ReviewStatus.AUTO_PASS.value,
            )
            return

        await self.repository.create_moderation_record(
            user_id=user_id,
            source=source,
            input_text=input_text,
            output_text=None,
            matched_words=",".join(matched_words),
            decision=ModerationDecision.BLOCK.value,
            review_status=ReviewStatus.AUTO_BLOCK.value,
            review_note="输入内容命中敏感词",
        )
        raise HTTPException(status_code=400, detail=f"输入内容命中敏感词: {','.join(matched_words)}")

    async def ensure_names_allowed(self, user_id: int, source: str, input_text: str, names: list):
        output_text = json.dumps([self._name_to_dict(name) for name in names], ensure_ascii=False)
        matched_words = await self._find_matched_words(output_text)
        if not matched_words:
            await self.repository.create_moderation_record(
                user_id=user_id,
                source=source,
                input_text=input_text,
                output_text=output_text,
                matched_words=None,
                decision=ModerationDecision.PASS.value,
                review_status=ReviewStatus.AUTO_PASS.value,
            )
            return

        await self.repository.create_moderation_record(
            user_id=user_id,
            source=source,
            input_text=input_text,
            output_text=output_text,
            matched_words=",".join(matched_words),
            decision=ModerationDecision.BLOCK.value,
            review_status=ReviewStatus.AUTO_BLOCK.value,
            review_note="AI 生成内容命中敏感词",
        )
        raise HTTPException(status_code=400, detail=f"AI 生成内容命中敏感词: {','.join(matched_words)}")

    def _name_to_dict(self, name):
        if hasattr(name, "model_dump"):
            return name.model_dump()
        if isinstance(name, dict):
            return name
        return {"name": str(name)}
