from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from typing import Optional
import os

class CachedStaticFiles(StaticFiles):
    """
    Класс для статических файлов с кэшированием.
    Устанавливает заголовки Cache-Control для улучшения производительности.
    """
    def __init__(self, directory: str, cache_time: int = 3600, **kwargs):
        """
        :param directory: Директория с файлами
        :param cache_time: Время кэширования в секундах (по умолчанию 1 час)
        """
        super().__init__(directory=directory, **kwargs)
        self.cache_time = cache_time

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        
        # Устанавливаем заголовки кэширования для успешного ответа
        if isinstance(response, FileResponse):
            # Устанавливаем заголовки кэширования
            response.headers["Cache-Control"] = f"public, max-age={self.cache_time}"
            response.headers["Expires"] = self.expires_header()
        
        return response

    def expires_header(self) -> str:
        """
        Генерирует заголовок Expires в формате HTTP.
        """
        from datetime import datetime, timedelta, timezone
        expires = datetime.now(timezone.utc) + timedelta(seconds=self.cache_time)
        return expires.strftime('%a, %d %b %Y %H:%M:%S GMT')