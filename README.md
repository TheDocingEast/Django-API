# NaviTime Kanban API

REST API для управления задачами по отделам. Построен на Django REST Framework с PostgreSQL и JWT-аутентификацией.

## Стек

- Python 3.14
- Django 5.2
- Django REST Framework
- PostgreSQL
- djangorestframework-simplejwt
- drf-spectacular (Swagger UI)
- drf-extensions

## Структура проекта

```
src/
├── manage.py
├── navitime_kanban/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── kanban/
    ├── migrations/
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── permissions.py
    ├── serializers.py
    ├── urls.py
    └── views.py
```

## Установка

### 1. Клонировать репозиторий

```bash
git clone <url>
cd Django-API
```

### 2. Создать и активировать виртуальное окружение

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Создать базу данных PostgreSQL

```bash
createdb -U postgres navitime_kanban
```

### 5. Настроить переменные окружения

Проект читает параметры БД из переменных окружения. Создайте файл `.env` или экспортируйте переменные:

```bash
export DB_NAME=navitime_kanban
export DB_USER=postgres
export DB_PASSWORD=ваш_пароль
export DB_HOST=127.0.0.1
```

### 6. Применить миграции

```bash
python manage.py migrate
```

### 7. Создать суперпользователя

```bash
python manage.py createsuperuser
```

### 8. Запустить сервер

```bash
python manage.py runserver 8080
```

## База данных

Проект использует пять таблиц согласно словарю БД:

| Таблица | Описание |
|---|---|
| `workspaces` | Рабочие пространства / отделы |
| `users` | Пользователи с ролями |
| `statuses` | Колонки Kanban-доски |
| `tasks` | Задачи с мягким удалением |
| `comments` | Комментарии к задачам |

## Роли пользователей

| Роль | Описание |
|---|---|
| `employee` | Сотрудник. Просмотр задач своего отдела, комментирование, пометка задач неактуальными |
| `manager` | Начальник. Создание, редактирование и удаление задач, управление статусами, мониторинг всех пространств |
| `admin` | Технический администратор. Полный доступ, управление пространствами и учётными записями |

## Аутентификация

Проект использует JWT-токены (Bearer). Для получения токена:

```bash
curl -X POST http://127.0.0.1:8080/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "логин", "password": "пароль"}'
```

Ответ:

```json
{
  "access": "...",
  "refresh": "..."
}
```

Использование токена в запросах:

```
Authorization: Bearer <access-токен>
```

Обновление access-токена:

```bash
curl -X POST http://127.0.0.1:8080/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "..."}'
```

## API Endpoints

Базовый URL: `http://127.0.0.1:8080/api/v1/`

### Рабочие пространства

| Метод | URL | Доступ |
|---|---|---|
| GET | `/workspaces/` | Все авторизованные |
| POST | `/workspaces/` | admin |
| DELETE | `/workspaces/{id}/` | admin |

### Пользователи

| Метод | URL | Доступ |
|---|---|---|
| GET | `/users/` | admin |
| POST | `/users/` | admin |
| PATCH | `/users/{id}/block/` | admin |
| PATCH | `/users/{id}/activate/` | admin |

Фильтрация: `?workspace_id=1`, `?role=employee`

### Статусы

| Метод | URL | Доступ |
|---|---|---|
| GET | `/statuses/` | Все авторизованные |
| POST | `/statuses/` | manager, admin |
| PUT / PATCH | `/statuses/{id}/` | manager, admin |
| DELETE | `/statuses/{id}/` | manager, admin |

Фильтрация: `?workspace_id=1`

### Задачи

| Метод | URL | Доступ |
|---|---|---|
| GET | `/tasks/` | Все авторизованные |
| POST | `/tasks/` | manager, admin |
| PATCH | `/tasks/{id}/` | manager, admin |
| DELETE | `/tasks/{id}/` | manager, admin |
| PATCH | `/tasks/{id}/mark_irrelevant/` | Все авторизованные |

Фильтрация: `?workspace_id=1`, `?status_id=2`, `?assignee_id=3`, `?priority=4`

Удаление мягкое — запись остаётся в БД с флагом `is_deleted=true`.

### Комментарии

| Метод | URL | Доступ |
|---|---|---|
| GET | `/comments/` | Все авторизованные |
| POST | `/comments/` | Все авторизованные |
| PUT / PATCH | `/comments/{id}/` | Автор или admin |
| DELETE | `/comments/{id}/` | Автор или admin |

Фильтрация: `?task_id=1`

## Документация

Swagger UI доступен по адресу:

```
http://127.0.0.1:8080/api/schema/swagger-ui/
```

OpenAPI-схема (для импорта в Postman):

```
http://127.0.0.1:8080/api/schema/
```

## Консольный клиент

В корне проекта находится `main.py` — интерактивный CLI-клиент для работы с API.

Установить зависимости клиента:

```bash
pip install httpx rich
```

Запустить:

```bash
python main.py
```

Перед использованием убедитесь, что в начале файла указан правильный порт:

```python
BASE_URL: str = "http://127.0.0.1:8080/api/v1"
AUTH_URL: str = "http://127.0.0.1:8080/api/token/"
```

## Административная панель

```
http://127.0.0.1:8080/admin/
```

Доступна после создания суперпользователя командой `createsuperuser`.

## Настройки JWT

В `settings.py`:

```python
SIMPLE_JWT = {
    'USER_ID_FIELD': 'user_id',
    'USER_ID_CLAIM': 'user_id',
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}
```

## Пагинация

Все списки возвращают по 20 объектов на страницу. Навигация через параметр `?page=2`.

```json
{
  "count": 100,
  "next": "http://127.0.0.1:8080/api/v1/tasks/?page=2",
  "previous": null,
  "results": []
}
```

## Троттлинг

| Тип пользователя | Лимит |
|---|---|
| Анонимный | 100 запросов / час |
| Авторизованный | 1000 запросов / час |

При превышении лимита сервер возвращает `429 Too Many Requests`.
