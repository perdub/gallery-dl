# coding: utf-8
import re
import base64
import urllib.parse
from .common import Extractor, Message

class SMGRedirectExtractor(Extractor):
    """
    Экстрактор-перехватчик для страниц подтверждения (link-confirmation).
    Достает конечную ссылку и передает её в очередь (Message.Queue) для других экстракторов.
    """
    category = "socialmediagirls"
    subcategory = "redirect"
    
    # Ловим ссылки вида: https://forums.socialmediagirls.com/goto/link-confirmation?url=aHR0cHM...
    pattern = r'https?://(?:www\.)?forums\.socialmediagirls\.com/goto/link-confirmation\?(?:[^&]+&)*url=(?P<b64url>[^&]+)'

    def items(self):
        # 1. Достаем параметр url из регулярки
        b64url = self.match.group('b64url')
        b64url = urllib.parse.unquote(b64url)
        
        real_url = None

        # Способ А (Быстрый): Пытаемся раскодировать Base64 без загрузки страницы
        # Формула с padding ('=') нужна, чтобы питон не ругался на длину строки
        padded_b64 = b64url + '=' * (-len(b64url) % 4)
        try:
            decoded_bytes = base64.urlsafe_b64decode(padded_b64)
            decoded_str = decoded_bytes.decode('utf-8')
            
            # Проверяем, действительно ли там спрятана ссылка
            if decoded_str.startswith('http'):
                real_url = decoded_str
                self.log.debug(f"Успешно раскодирован Base64: {real_url}")
        except Exception as e:
            self.log.debug(f"Не удалось раскодировать Base64: {e}")

        # Способ Б (Запасной, как ты и просил с HTML): 
        # Если вдруг Base64 не сработал, качаем страницу и вырезаем из HTML
        if not real_url:
            self.log.info("Скачиваем страницу для поиска кнопки...")
            response = self.request(self.url)
            
            # Ищем <a href="..." class="button button--cta ...">
            match = re.search(r'<a\s+href="([^"]+)"[^>]*class="[^"]*button--cta', response.text)
            if match:
                real_url = match.group(1)
            else:
                self.log.error("Не удалось найти кнопку перехода в HTML.")
                return

        # 2. Передаем ссылку дальше в gallery-dl
        if real_url:
            self.log.info(f"Перенаправляю обработку на: {real_url}")
            
            # Вместо Message.Url делаем Message.Queue !
            # Программа увидит это и вызовет твой GoonboxExtractor для новой ссылки
            yield Message.Queue, real_url, {}
