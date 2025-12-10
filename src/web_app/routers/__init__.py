from .courses import router as courses_router
from .topics import router as topics_router
from .menu_items import router as menu_items_router

__all__ = ["courses_router", "topics_router", "menu_items_router"]