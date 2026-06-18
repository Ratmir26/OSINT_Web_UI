# OSINT Web UI

Веб-интерфейс для OSINT-разведки. Переиспользует те же модули, что и [TG OSINT Bot](https://github.com/Ratmir26/TG_OSINT_Bot).

Стек: **Flask + Bootstrap 5** (тёмная тема).

## Модули

| Роут | Описание |
|---|---|
| `/` | Главная с карточками модулей |
| `/search` | OSINT-поиск компании/человека |
| `/phone` | Пробив номера телефона |
| `/email` | Проверка email в утечках |
| `/ip` | WHOIS, DNS, IP геолокация |
| `/name` | Поиск человека в VK, OK, Facebook |
| `/telegram` | Поиск в Telegram |
| `/marketplace` | Поиск на Wildberries и Ozon |
| `/avito` | Поиск на Avito и Юле |
| `/youtube` | Поиск каналов YouTube |
| `/compare` | Сравнение двух компаний |
| `/graph` | Визуализация связей (граф) |
| `/history` | История запросов |
| `/mass` | Массовый пробив номеров |

## Установка

```bash
git clone https://github.com/Ratmir26/OSINT_Web_UI.git
cd OSINT_Web_UI
pip install -r requirements.txt
```

## Запуск

```bash
python app.py
```

Откройте в браузере: **http://localhost:5000**

Для доступа с других устройств в той же сети используйте `http://192.168.x.x:5000`.

## Структура

```
OSINT_Web_UI/
├── app.py                  # Flask-приложение, 17 роутов
├── config.py               # Конфигурация
├── osint_agent.py          # Ядро OSINT (DuckDuckGo + 2GIS + Яндекс)
├── modules/                # Все модули поиска
├── utils/                  # Вспомогательные утилиты
├── templates/              # 15 HTML-шаблонов (Bootstrap 5 dark)
│   ├── base.html           # Каркас с боковым меню
│   └── *.html              # Страницы модулей
├── static/
│   ├── css/style.css       # Дополнительные стили
│   └── js/main.js          # Скрипты
└── data/
    └── results/            # Сохранённые отчёты
```

## Требования

- Python 3.9+
- Flask (устанавливается из requirements.txt)

## Лицензия

MIT
