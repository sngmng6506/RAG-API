"""
Jinja2 기반 프롬프트 로더.
프롬프트는 .j2 템플릿으로 관리하며, render()로 변수를 채워 문자열을 반환합니다.
"""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_PROMPTS_DIR = Path(__file__).resolve().parent
_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    autoescape=select_autoescape(enabled_extensions=()),  # 프롬프트는 HTML 이스케이프 불필요
)


def render(name: str, **context) -> str:
    """
    지정한 이름의 .j2 템플릿을 렌더링합니다.
    name에 확장자를 붙이지 않으면 자동으로 .j2를 붙입니다.
    """
    template_name = f"{name}.j2" if not name.endswith(".j2") else name
    template = _env.get_template(template_name)
    return template.render(**context).strip()
