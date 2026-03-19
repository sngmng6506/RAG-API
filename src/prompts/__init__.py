"""프롬프트는 Jinja2(.j2) 템플릿으로 관리합니다. 렌더링은 loader.render()를 사용하세요."""
from .loader import render

__all__ = ["render"]
