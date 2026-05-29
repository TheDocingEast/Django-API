import httpx
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

console = Console()

BASE_URL: str = "http://127.0.0.1:8080/api/v1"
AUTH_URL: str = "http://127.0.0.1:8080/api/token/"

# ── Глобальное состояние сессии ──────────────────────────────────────────────
ACCESS_TOKEN: str | None = None
CURRENT_USER: dict | None = None
CURRENT_WORKSPACE_ID: int | None = None


# ─────────────────────────── helpers ────────────────────────────

def _headers() -> dict:
    """Возвращает заголовки с Bearer-токеном, если пользователь авторизован."""
    if ACCESS_TOKEN:
        return {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    return {}


def _print_rtt(response: httpx.Response) -> None:
    elapsed = response.elapsed.total_seconds() * 1000
    color = "green" if elapsed < 100 else ("yellow" if elapsed < 300 else "red")
    console.print(
        f"  Status: [bold]{response.status_code}[/bold] | "
        f"RTT: [{color}]{elapsed:.2f}ms[/{color}]"
    )


def _get(path: str, params: dict | None = None) -> dict | list | None:
    try:
        with console.status("[bold green]Sending request..."):
            r = httpx.get(f"{BASE_URL}{path}", headers=_headers(), params=params, timeout=10)
        _print_rtt(r)
        if r.status_code == 401:
            console.print("[red]Ошибка 401:[/red] Необходима авторизация. Используйте опцию [bold]L[/bold].")
            return None
        if r.status_code == 403:
            console.print("[red]Ошибка 403:[/red] Недостаточно прав для выполнения операции.")
            return None
        if not r.is_success:
            console.print(f"[red]Ошибка {r.status_code}:[/red] {r.text[:200]}")
            return None
        return r.json()
    except httpx.RequestError as e:
        console.print(f"[red]Запрос не выполнен:[/red] {e}")
        return None


def _post(path: str, body: dict, base: str | None = None) -> dict | None:
    url_base = base or BASE_URL
    try:
        with console.status("[bold green]Sending request..."):
            r = httpx.post(f"{url_base}{path}", json=body, headers=_headers(), timeout=10)
        _print_rtt(r)
        if r.status_code == 401:
            console.print("[red]Ошибка 401:[/red] Необходима авторизация. Используйте опцию [bold]L[/bold].")
            return None
        if r.status_code == 403:
            console.print("[red]Ошибка 403:[/red] Недостаточно прав для выполнения операции.")
            return None
        if not r.is_success:
            console.print(f"[red]Ошибка {r.status_code}:[/red] {r.text[:200]}")
            return None
        return r.json()
    except httpx.RequestError as e:
        console.print(f"[red]Запрос не выполнен:[/red] {e}")
        return None


def _patch(path: str, body: dict) -> dict | None:
    try:
        with console.status("[bold green]Sending request..."):
            r = httpx.patch(f"{BASE_URL}{path}", json=body, headers=_headers(), timeout=10)
        _print_rtt(r)
        if r.status_code == 401:
            console.print("[red]Ошибка 401:[/red] Необходима авторизация.")
            return None
        if r.status_code == 403:
            console.print("[red]Ошибка 403:[/red] Недостаточно прав.")
            return None
        if not r.is_success:
            console.print(f"[red]Ошибка {r.status_code}:[/red] {r.text[:200]}")
            return None
        return r.json()
    except httpx.RequestError as e:
        console.print(f"[red]Запрос не выполнен:[/red] {e}")
        return None


def _delete(path: str, params: dict | None = None) -> bool:
    try:
        with console.status("[bold green]Sending request..."):
            r = httpx.delete(f"{BASE_URL}{path}", headers=_headers(), params=params, timeout=10)
        _print_rtt(r)
        if r.status_code in (204, 200):
            return True
        if r.status_code == 403:
            console.print("[red]Ошибка 403:[/red] Недостаточно прав.")
        else:
            console.print(f"[red]Ошибка {r.status_code}:[/red] {r.text[:200]}")
        return False
    except httpx.RequestError as e:
        console.print(f"[red]Запрос не выполнен:[/red] {e}")
        return False


def _require_auth() -> bool:
    """Возвращает True если пользователь авторизован."""
    if ACCESS_TOKEN is None:
        console.print(
            "[yellow]Вы не авторизованы.[/yellow] "
            "Используйте опцию [bold]L[/bold] для входа."
        )
        return False
    return True


def _require_workspace() -> bool:
    """Возвращает True если выбрано рабочее пространство."""
    if CURRENT_WORKSPACE_ID is None:
        console.print(
            "[yellow]Не выбрано рабочее пространство.[/yellow] "
            "Используйте опцию [bold]W[/bold]."
        )
        return False
    return True


def _priority_label(p: int) -> str:
    return {1: "[dim]Низкий[/dim]", 2: "[cyan]Средний[/cyan]",
            3: "[yellow]Высокий[/yellow]", 4: "[bold red]Критический[/bold red]"}.get(p, str(p))


# ─────────────────────────── auth ────────────────────────────

def do_login() -> None:
    global ACCESS_TOKEN, CURRENT_USER
    username = console.input("  > Логин: ").strip()
    password = console.input("  > Пароль: ").strip()
    try:
        with console.status("[bold green]Sending request..."):
            r = httpx.post(
                AUTH_URL,
                json={"username": username, "password": password},
                timeout=10,
            )
        _print_rtt(r)
        if r.status_code == 200:
            data = r.json()
            ACCESS_TOKEN = data["access"]
            console.print(f"[green]✓ Авторизован как[/green] [bold cyan]{username}[/bold cyan]")
        else:
            console.print(f"[red]Авторизация не удалась:[/red] {r.text[:200]}")
    except httpx.RequestError as e:
        console.print(f"[red]Запрос не выполнен:[/red] {e}")


def do_logout() -> None:
    global ACCESS_TOKEN, CURRENT_USER, CURRENT_WORKSPACE_ID
    ACCESS_TOKEN = None
    CURRENT_USER = None
    CURRENT_WORKSPACE_ID = None
    console.print("[yellow]Выход выполнен.[/yellow]")


# ─────────────────────────── workspaces ────────────────────────────

def list_workspaces() -> None:
    """Сценарий 7: список всех рабочих пространств."""
    if not _require_auth():
        return
    data = _get("/workspaces/")
    if not data:
        return
    results = data.get("results", data) if isinstance(data, dict) else data
    table = Table(title="Рабочие пространства", box=box.SIMPLE_HEAD)
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Название", style="bold cyan")
    table.add_column("Создано", style="dim")
    for ws in results:
        table.add_row(str(ws["workspace_id"]), ws["name"], ws.get("created_at", "")[:10])
    console.print(table)


def select_workspace() -> None:
    """Выбрать рабочее пространство для работы с доской."""
    global CURRENT_WORKSPACE_ID
    if not _require_auth():
        return
    list_workspaces()
    ws_id = console.input("  > Введите ID пространства: ").strip()
    if ws_id.isdigit():
        CURRENT_WORKSPACE_ID = int(ws_id)
        console.print(f"[green]✓ Выбрано пространство ID={CURRENT_WORKSPACE_ID}[/green]")
    else:
        console.print("[red]Некорректный ID.[/red]")


def create_workspace() -> None:
    """Сценарий 11: создание рабочего пространства (только admin)."""
    if not _require_auth():
        return
    name = console.input("  > Название нового отдела: ").strip()
    if not name:
        return
    data = _post("/workspaces/", {"name": name})
    if data:
        console.print(f"[green]✓ Создан отдел:[/green] [bold cyan]{data['name']}[/bold cyan] (ID={data['workspace_id']})")


# ─────────────────────────── statuses ────────────────────────────

def list_statuses() -> None:
    """Сценарий 2: статусы-колонки текущего рабочего пространства."""
    if not _require_auth() or not _require_workspace():
        return
    data = _get("/statuses/", params={"workspace_id": CURRENT_WORKSPACE_ID})
    if not data:
        return
    results = data.get("results", data) if isinstance(data, dict) else data
    table = Table(title=f"Статусы пространства ID={CURRENT_WORKSPACE_ID}", box=box.SIMPLE_HEAD)
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Название", style="bold cyan")
    table.add_column("Позиция", justify="center")
    table.add_column("Цвет", style="green")
    for s in results:
        table.add_row(
            str(s["status_id"]),
            s["name"],
            str(s["position"]),
            s.get("color") or "—",
        )
    console.print(table)


def create_status() -> None:
    """Сценарий 10: добавление нового статуса (manager/admin)."""
    if not _require_auth() or not _require_workspace():
        return
    name = console.input("  > Название статуса (напр. 'In Progress'): ").strip()
    position = console.input("  > Позиция (порядковый номер): ").strip()
    color = console.input("  > Цвет HEX (#RRGGBB, Enter — пропустить): ").strip() or None
    if not name or not position.isdigit():
        console.print("[red]Название и позиция обязательны.[/red]")
        return
    body = {"workspace_id": CURRENT_WORKSPACE_ID, "name": name, "position": int(position)}
    if color:
        body["color"] = color
    data = _post("/statuses/", body)
    if data:
        console.print(f"[green]✓ Статус создан:[/green] [bold cyan]{data['name']}[/bold cyan] (ID={data['status_id']})")


# ─────────────────────────── tasks ────────────────────────────

def list_tasks() -> None:
    """Сценарий 2: просмотр Kanban-доски — задачи текущего пространства."""
    if not _require_auth() or not _require_workspace():
        return
    params: dict = {"workspace_id": CURRENT_WORKSPACE_ID}

    # Необязательная фильтрация
    status_filter = console.input("  > Фильтр по status_id (Enter — пропустить): ").strip()
    if status_filter.isdigit():
        params["status_id"] = int(status_filter)

    data = _get("/tasks/", params=params)
    if not data:
        return
    results = data.get("results", data) if isinstance(data, dict) else data
    if not results:
        console.print("[dim]Задач не найдено.[/dim]")
        return

    table = Table(
        title=f"Задачи пространства ID={CURRENT_WORKSPACE_ID}",
        box=box.SIMPLE_HEAD,
        show_lines=True,
    )
    table.add_column("ID", style="dim", justify="right", no_wrap=True)
    table.add_column("Заголовок", style="bold white", max_width=30)
    table.add_column("Статус", style="cyan")
    table.add_column("Приоритет", justify="center")
    table.add_column("Исполнитель", style="yellow")
    table.add_column("Дедлайн", style="dim")

    for t in results:
        status_name = t.get("status", {}).get("name", "—") if isinstance(t.get("status"), dict) else "—"
        assignee = t.get("assignee") or {}
        assignee_name = assignee.get("full_name", "—") if assignee else "—"
        deadline = (t.get("deadline") or "—")[:10]
        table.add_row(
            str(t["task_id"]),
            t["title"],
            status_name,
            _priority_label(t.get("priority", 2)),
            assignee_name,
            deadline,
        )
    console.print(table)

    total = data.get("count", len(results)) if isinstance(data, dict) else len(results)
    console.print(f"  [dim]Всего задач: {total}[/dim]")


def view_task() -> None:
    """Сценарий 3: детальный просмотр карточки задачи."""
    if not _require_auth():
        return
    task_id = console.input("  > ID задачи: ").strip()
    if not task_id.isdigit():
        console.print("[red]Некорректный ID.[/red]")
        return
    t = _get(f"/tasks/{task_id}/")
    if not t:
        return

    status_name = t.get("status", {}).get("name", "—") if isinstance(t.get("status"), dict) else "—"
    assignee = t.get("assignee") or {}
    creator = t.get("creator") or {}
    content = (
        f"[bold white]{t['title']}[/bold white]\n\n"
        f"[dim]Описание:[/dim] {t.get('description') or '—'}\n\n"
        f"[dim]Статус:[/dim]     [cyan]{status_name}[/cyan]\n"
        f"[dim]Приоритет:[/dim]  {_priority_label(t.get('priority', 2))}\n"
        f"[dim]Исполнитель:[/dim] [yellow]{assignee.get('full_name', '—')}[/yellow]\n"
        f"[dim]Создал:[/dim]     {creator.get('full_name', '—')}\n"
        f"[dim]Дедлайн:[/dim]   [bold]{(t.get('deadline') or '—')[:16]}[/bold]\n"
        f"[dim]Создано:[/dim]   {t.get('created_at', '—')[:16]}\n"
        f"[dim]Изменено:[/dim]  {t.get('updated_at', '—')[:16]}"
    )
    console.print(Panel(content, title=f"[bold cyan]Задача #{task_id}[/bold cyan]", width=60))

    # Комментарии
    comments_data = _get("/comments/", params={"task_id": task_id})
    if comments_data:
        comments = comments_data.get("results", comments_data) if isinstance(comments_data, dict) else comments_data
        if comments:
            console.print(f"\n  [bold]Комментарии ({len(comments)}):[/bold]")
            for c in comments:
                author = c.get("author") or {}
                console.print(
                    f"  [dim]{c.get('created_at', '')[:16]}[/dim] "
                    f"[yellow]{author.get('full_name', '—')}:[/yellow] {c['body']}"
                )


def create_task() -> None:
    """Сценарий 8: создание задачи (manager/admin)."""
    if not _require_auth() or not _require_workspace():
        return

    list_statuses()
    title = console.input("  > Заголовок задачи: ").strip()
    if not title:
        console.print("[red]Заголовок обязателен.[/red]")
        return
    description = console.input("  > Описание (Enter — пропустить): ").strip() or None
    status_id = console.input("  > ID статуса (начальный): ").strip()
    assignee_id = console.input("  > ID исполнителя (Enter — без исполнителя): ").strip() or None
    priority = console.input("  > Приоритет [1-низкий / 2-средний / 3-высокий / 4-крит] (Enter=2): ").strip() or "2"
    deadline = console.input("  > Дедлайн (YYYY-MM-DDTHH:MM, Enter — без дедлайна): ").strip() or None

    if not status_id.isdigit():
        console.print("[red]Некорректный ID статуса.[/red]")
        return

    body: dict = {
        "title": title,
        "workspace_id": CURRENT_WORKSPACE_ID,
        "status_id": int(status_id),
        "priority": int(priority) if priority.isdigit() else 2,
    }
    if description:
        body["description"] = description
    if assignee_id and assignee_id.isdigit():
        body["assignee_id"] = int(assignee_id)
    if deadline:
        body["deadline"] = deadline

    data = _post("/tasks/", body)
    if data:
        console.print(f"[green]✓ Задача создана:[/green] [bold cyan]{data['title']}[/bold cyan] (ID={data['task_id']})")


def move_task() -> None:
    """Сценарий 4: перемещение задачи между статусами (Drag-and-Drop)."""
    if not _require_auth():
        return
    task_id = console.input("  > ID задачи: ").strip()
    if not _require_workspace():
        return
    list_statuses()
    new_status_id = console.input("  > Новый ID статуса: ").strip()
    if not task_id.isdigit() or not new_status_id.isdigit():
        console.print("[red]Некорректные данные.[/red]")
        return
    data = _patch(f"/tasks/{task_id}/", {"status_id": int(new_status_id)})
    if data:
        status_name = data.get("status", {}).get("name", new_status_id) if isinstance(data.get("status"), dict) else new_status_id
        console.print(f"[green]✓ Задача #{task_id} перемещена в статус:[/green] [bold cyan]{status_name}[/bold cyan]")


def mark_task_irrelevant() -> None:
    """Сценарий 6: пометить задачу как неактуальную."""
    if not _require_auth():
        return
    task_id = console.input("  > ID задачи: ").strip()
    if not task_id.isdigit():
        console.print("[red]Некорректный ID.[/red]")
        return
    data = _patch(f"/tasks/{task_id}/mark_irrelevant/", {})
    if data:
        console.print(f"[yellow]✓ Задача #{task_id} помечена как неактуальная.[/yellow]")


def delete_task() -> None:
    """Сценарий 9: мягкое удаление задачи (manager/admin). is_deleted=True."""
    if not _require_auth():
        return
    task_id = console.input("  > ID задачи для удаления: ").strip()
    if not task_id.isdigit():
        console.print("[red]Некорректный ID.[/red]")
        return
    confirm = console.input(f"  [red]Удалить задачу #{task_id}? (y/n):[/red] ").strip().lower()
    if confirm != "y":
        console.print("[dim]Отменено.[/dim]")
        return
    if _delete(f"/tasks/{task_id}/"):
        console.print(f"[green]✓ Задача #{task_id} удалена (мягко, is_deleted=1).[/green]")


# ─────────────────────────── comments ────────────────────────────

def add_comment() -> None:
    """Сценарий 5: добавление комментария к задаче."""
    if not _require_auth():
        return
    task_id = console.input("  > ID задачи: ").strip()
    if not task_id.isdigit():
        console.print("[red]Некорректный ID.[/red]")
        return
    body = console.input("  > Текст комментария: ").strip()
    if not body:
        console.print("[red]Комментарий не может быть пустым.[/red]")
        return
    data = _post("/comments/", {"task_id": int(task_id), "body": body})
    if data:
        console.print(f"[green]✓ Комментарий добавлен (ID={data['comment_id']}).[/green]")


# ─────────────────────────── users ────────────────────────────

def list_users() -> None:
    """Сценарий 12: список пользователей (только admin)."""
    if not _require_auth():
        return
    params = {}
    ws_filter = console.input("  > Фильтр по workspace_id (Enter — все): ").strip()
    if ws_filter.isdigit():
        params["workspace_id"] = ws_filter
    role_filter = console.input("  > Фильтр по role [employee/manager/admin] (Enter — все): ").strip()
    if role_filter:
        params["role"] = role_filter

    data = _get("/users/", params=params if params else None)
    if not data:
        return
    results = data.get("results", data) if isinstance(data, dict) else data

    table = Table(title="Пользователи", box=box.SIMPLE_HEAD)
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Логин", style="bold cyan")
    table.add_column("Имя", style="white")
    table.add_column("Роль", style="yellow")
    table.add_column("Отдел", style="green")
    table.add_column("Активен", justify="center")
    for u in results:
        ws = u.get("workspace") or {}
        table.add_row(
            str(u["user_id"]),
            u["username"],
            u["full_name"],
            u["role"],
            ws.get("name", "—") if ws else "—",
            "[green]✓[/green]" if u.get("is_active") else "[red]✗[/red]",
        )
    console.print(table)


def create_user() -> None:
    """Сценарий 12: создание пользователя (только admin)."""
    if not _require_auth():
        return
    username = console.input("  > Логин: ").strip()
    password = console.input("  > Пароль: ").strip()
    full_name = console.input("  > Полное имя: ").strip()
    role = console.input("  > Роль [employee / manager / admin]: ").strip()
    list_workspaces()
    ws_id = console.input("  > ID рабочего пространства (Enter — без пространства): ").strip()

    if not all([username, password, full_name, role]):
        console.print("[red]Все поля обязательны.[/red]")
        return

    body: dict = {"username": username, "password": password, "full_name": full_name, "role": role}
    if ws_id.isdigit():
        body["workspace_id"] = int(ws_id)

    data = _post("/users/", body)
    if data:
        console.print(f"[green]✓ Пользователь создан:[/green] [bold cyan]{data['username']}[/bold cyan] (ID={data['user_id']})")


def block_user() -> None:
    """Сценарий 12: блокировка учётной записи пользователя (only admin)."""
    if not _require_auth():
        return
    list_users()
    user_id = console.input("  > ID пользователя для блокировки: ").strip()
    if not user_id.isdigit():
        console.print("[red]Некорректный ID.[/red]")
        return
    data = _patch(f"/users/{user_id}/block/", {})
    if data:
        console.print(f"[yellow]✓ Пользователь #{user_id} заблокирован.[/yellow]")


# ─────────────────────────── menu ────────────────────────────

def show_menu() -> str:
    user_info = (
        f"[bold cyan]{CURRENT_USER['username']}[/bold cyan] "
        f"([yellow]{CURRENT_USER['role']}[/yellow])"
        if CURRENT_USER else "[dim]не авторизован[/dim]"
    )
    ws_info = (
        f"[bold cyan]ID={CURRENT_WORKSPACE_ID}[/bold cyan]"
        if CURRENT_WORKSPACE_ID else "[dim]не выбрано[/dim]"
    )

    menu = Text()
    menu.append(f"Пользователь:  {user_info}\n")
    menu.append(f"Пространство:  {ws_info}\n\n")

    menu.append("  ── Сессия ─────────────────────────────\n", style="dim")
    menu.append("  [L]  Войти в систему\n",                    style="white")
    menu.append("  [O]  Выйти\n\n",                            style="white")

    menu.append("  ── Пространства и статусы ─────────────\n", style="dim")
    menu.append("  [W]  Выбрать рабочее пространство\n",       style="cyan")
    menu.append("  [WL] Список пространств\n",                 style="cyan")
    menu.append("  [WC] Создать пространство (admin)\n",       style="cyan")
    menu.append("  [SL] Статусы текущего пространства\n",      style="cyan")
    menu.append("  [SC] Создать статус (manager+)\n\n",        style="cyan")

    menu.append("  ── Задачи ─────────────────────────────\n", style="dim")
    menu.append("  [TL] Просмотр доски (список задач)\n",      style="white")
    menu.append("  [TV] Детали задачи\n",                      style="white")
    menu.append("  [TC] Создать задачу (manager+)\n",          style="white")
    menu.append("  [TM] Переместить задачу (сменить статус)\n", style="white")
    menu.append("  [TI] Пометить задачу неактуальной\n",       style="white")
    menu.append("  [TD] Удалить задачу (manager+)\n\n",        style="white")

    menu.append("  ── Комментарии ────────────────────────\n", style="dim")
    menu.append("  [CC] Добавить комментарий\n\n",             style="white")

    menu.append("  ── Пользователи (admin) ───────────────\n", style="dim")
    menu.append("  [UL] Список пользователей\n",               style="yellow")
    menu.append("  [UC] Создать пользователя\n",               style="yellow")
    menu.append("  [UB] Заблокировать пользователя\n\n",       style="yellow")

    menu.append("  [Q]  Выход\n", style="red")

    console.print(Panel(
        menu,
        title="[bold cyan]📋 NAVITIME KANBAN CLIENT[/bold cyan]",
        width=56,
    ))
    return console.input("  [bold green]>[/bold green] Введите опцию: ").strip().lower()


# ─────────────────────────── App ────────────────────────────

class App:
    def __init__(self) -> None:
        running = True
        while running:
            choice = show_menu()
            match choice:
                # ── Сессия ──
                case "l":
                    do_login()
                case "o":
                    do_logout()

                # ── Пространства ──
                case "w":
                    select_workspace()
                case "wl":
                    list_workspaces()
                case "wc":
                    create_workspace()

                # ── Статусы ──
                case "sl":
                    list_statuses()
                case "sc":
                    create_status()

                # ── Задачи ──
                case "tl":
                    list_tasks()
                case "tv":
                    view_task()
                case "tc":
                    create_task()
                case "tm":
                    move_task()
                case "ti":
                    mark_task_irrelevant()
                case "td":
                    delete_task()

                # ── Комментарии ──
                case "cc":
                    add_comment()

                # ── Пользователи ──
                case "ul":
                    list_users()
                case "uc":
                    create_user()
                case "ub":
                    block_user()

                # ── Выход ──
                case "q":
                    console.print("[red]До свидания![/red]")
                    running = False
                case _:
                    console.print("[red]Неизвестная опция.[/red]")


if __name__ == "__main__":
    App()
