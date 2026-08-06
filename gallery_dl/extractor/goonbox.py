# coding: utf-8
from .common import Extractor, Message
from .. import exception

class GoonboxImageExtractor(Extractor):
    """
    Экстрактор для изображений с сайта goonbox.cr.
    Использует внутреннее API, передавая жесткие заголовки браузера,
    чтобы обойти базовую защиту (работает без куки).
    """
    category = "goonbox"
    subcategory = "image"
    
    # Ловим ссылки вида https://goonbox.cr/img/aBZF0iA
    pattern = r'https?://(?:www\.)?goonbox\.cr/img/(?P<id>[a-zA-Z0-9_-]+)'

    def __init__(self, match):
        super().__init__(match)
        self.image_id = match.group('id')

    def items(self):
        # 1. Заголовки для API (из рабочего curl запроса)
        headers = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9,ru;q=0.8',
            'referer': self.url,
            'sec-ch-ua': '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-requested-with': 'XMLHttpRequest',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'
        }

        # 2. API URL
        api_url = f'https://goonbox.cr/api/images/{self.image_id}'
        
        self.log.debug(f'Fetching API: {api_url}')

        try:
            # Делаем запрос к API
            response = self.request(api_url, headers=headers)
            json_data = response.json()
            
            # Вытаскиваем блок image, если он есть
            data = json_data.get('image') if 'image' in json_data else json_data
            
        except exception.HttpError as e:
            if e.code == 404:
                self.log.error(f"Image {self.image_id} not found (404).")
                return
            raise exception.StopExtraction(f'API Error: {e}')
        except Exception as e:
            raise exception.StopExtraction(f'Failed to fetch/parse API: {e}')

        # Проверяем, есть ли ссылка
        if not data or not data.get('original_url'):
            self.log.warning(f"No original URL found for image {self.image_id}")
            return

        file_url = data['original_url']

        # 3. Данные файла
        # Пробуем достать расширение из оригинального названия или mime-типа
        original_filename = data.get('original_filename', '')
        if original_filename and '.' in original_filename:
            ext = original_filename.rpartition('.')[2]
        else:
            ext = data.get('mime', '').split('/')[-1] if data.get('mime') else 'jpg'

        file_id = str(data.get('encoded_id') or self.image_id)
        filename = original_filename or f"{file_id}.{ext}"

        # Достаем автора (в goonbox он лежит в uploader или image.user)
        uploader = json_data.get("uploader", {}) or data.get("user", {})
        username = uploader.get("username", "unknown")

        # 4. Формируем словарь метаданных
        post_data = {
            "url": file_url,
            "filename": filename,
            "extension": ext,
            "id": file_id,
            "width": data.get("width"),
            "height": data.get("height"),
            "uploader": username,
            "created_at": data.get("created_at"),
            "_headers": headers  # Прокидываем заголовки, если загрузчику они понадобятся
        }

        # 5. Возвращаем кортежи
        
        # Сообщаем папку/метаданные галереи
        yield Message.Directory, post_data
        
        # Сообщаем сам файл для скачивания
        yield Message.Url, file_url, post_data
