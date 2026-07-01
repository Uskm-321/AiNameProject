from settings import INVITE_REGISTER_LINK_TEMPLATE


def build_invite_register_link(base_url: str, invite_code: str) -> str:
    template = (INVITE_REGISTER_LINK_TEMPLATE or "").strip()
    if template:
        return template.format(invite_code=invite_code)
    origin = str(base_url).rstrip("/")
    return f"{origin}/#/pages/register/register?invite_code={invite_code}"
