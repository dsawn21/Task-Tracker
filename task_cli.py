#!/usr/bin/env python3
"""Личный список дел. Задачи хранятся в tasks.json рядом с этим файлом."""

import json
import shlex
import sys
from datetime import datetime
from pathlib import Path

FILE = Path(__file__).resolve().parent / "tasks.json"

TODO, DOING, DONE = "todo", "in-progress", "done"
LABEL = {TODO: "ждёт", DOING: "в работе", DONE: "готово"}

HELP = f"""
Список дел → {FILE}

  1 add текст...           добавить (кавычки не обязательны)
  2 start <id>             взять в работу
  3 done <id>              закрыть
  4 todo <id>              вернуть в ожидание
  5 upd <id> текст...      поменять формулировку
  6 rm <id>                удалить
  7 ls [todo|работа|готово|все]

Цифра в начале — команда, не номер задачи. Номер задачи вторым: 3 2
Задачу, которая начинается с 1–7, добавляй через add.

Без команды — незакрытые задачи.
Без аргументов — то же самое, дальше можно писать команды в строке.
""".strip()


class Fail(Exception):
    """Сообщение пользователю, не traceback."""


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")  # noqa: DTZ005


def load():
    if not FILE.exists():
        return []
    try:
        raw = FILE.read_text(encoding="utf-8").strip()
        data = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        raise Fail(f"{FILE.name} повреждён. Почини JSON или удали файл.")
    except OSError as e:
        raise Fail(f"не читается {FILE}: {e}")
    if not isinstance(data, list):
        raise Fail(f"{FILE.name} должен быть списком задач.")
    return data


def save(tasks):
    try:
        FILE.write_text(
            json.dumps(tasks, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as e:
        raise Fail(f"не пишется {FILE}: {e}")


def as_id(value):
    try:
        return int(value)
    except ValueError:
        raise Fail(f"нужен номер задачи, а не {value!r}")


def find(tasks, task_id):
    for task in tasks:
        if task.get("id") == task_id:
            return task
    raise Fail(f"нет задачи #{task_id}")


def phrase(parts):
    text = " ".join(parts).strip()
    if not text:
        raise Fail("напиши текст задачи")
    return text


def print_list(tasks):
    if not tasks:
        print("пусто")
        return
    for task in tasks:
        status = LABEL.get(task.get("status"), task.get("status", "?"))
        print(f"#{task['id']:<3} {status:<9} {task['description']}")


def cmd_add(args):
    tasks = load()
    new_id = max((t["id"] for t in tasks), default=0) + 1
    stamp = now()
    tasks.append(
        {
            "id": new_id,
            "description": phrase(args),
            "status": TODO,
            "createdAt": stamp,
            "updatedAt": stamp,
        }
    )
    save(tasks)
    print(f"#{new_id} добавлена")


def cmd_upd(args):
    if len(args) < 2:
        raise Fail("upd <id> новый текст")
    tasks = load()
    task = find(tasks, as_id(args[0]))
    task["description"] = phrase(args[1:])
    task["updatedAt"] = now()
    save(tasks)
    print(f"#{task['id']} обновлена")


def cmd_rm(args):
    if len(args) != 1:
        raise Fail("rm <id>")
    tasks = load()
    task = find(tasks, as_id(args[0]))
    tasks.remove(task)
    save(tasks)
    print(f"#{task['id']} удалена")


def cmd_mark(args, status):
    if len(args) != 1:
        raise Fail("нужен один id")
    tasks = load()
    task = find(tasks, as_id(args[0]))
    task["status"] = status
    task["updatedAt"] = now()
    save(tasks)
    print(f"#{task['id']} — {LABEL[status]}")


def cmd_start(args):
    cmd_mark(args, DOING)


def cmd_done(args):
    cmd_mark(args, DONE)


def cmd_todo(args):
    cmd_mark(args, TODO)


FILTERS = {
    None: "open",
    "open": "open",
    "todo": TODO,
    "ждёт": TODO,
    "ждет": TODO,
    "in-progress": DOING,
    "doing": DOING,
    "работа": DOING,
    "done": DONE,
    "готово": DONE,
    "all": "all",
    "все": "all",
}


def cmd_ls(args):
    if len(args) > 1:
        raise Fail("ls [todo|работа|готово|все]")
    key = args[0] if args else None
    if key not in FILTERS:
        raise Fail("фильтр: todo, работа, готово, все")
    kind = FILTERS[key]
    tasks = load()
    if kind == "open":
        tasks = [t for t in tasks if t.get("status") != DONE]
    elif kind != "all":
        tasks = [t for t in tasks if t.get("status") == kind]
    print_list(tasks)


COMMANDS = {
    "add": cmd_add,
    "a": cmd_add,
    "upd": cmd_upd,
    "u": cmd_upd,
    "update": cmd_upd,
    "rm": cmd_rm,
    "del": cmd_rm,
    "delete": cmd_rm,
    "start": cmd_start,
    "s": cmd_start,
    "mark-in-progress": cmd_start,
    "done": cmd_done,
    "x": cmd_done,
    "mark-done": cmd_done,
    "todo": cmd_todo,
    "ls": cmd_ls,
    "l": cmd_ls,
    "list": cmd_ls,
}

# Только 1–7. Остальные числа — текст задачи (через add) или id вторым аргументом.
COMMANDS.update(
    {
        "1": cmd_add,
        "2": cmd_start,
        "3": cmd_done,
        "4": cmd_todo,
        "5": cmd_upd,
        "6": cmd_rm,
        "7": cmd_ls,
    }
)


def run(argv):
    if not argv:
        cmd_ls([])
        return
    if argv[0] in ("-h", "--help", "help"):
        print(HELP)
        return
    name, rest = argv[0], argv[1:]
    handler = COMMANDS.get(name)
    if handler is None:
        # `python task_cli.py купить хлеб` = добавить
        handler, rest = cmd_add, argv
    handler(rest)


def loop():
    cmd_ls([])
    print("1–7 или команда  |  q — выход  |  help")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line or line in ("q", "quit", "exit"):
            return
        try:
            run(shlex.split(line, posix=False))
        except Fail as e:
            print(f"ошибка: {e}", file=sys.stderr)


def main(argv):
    try:
        if not argv:
            loop()
        else:
            run(argv)
    except Fail as e:
        print(f"ошибка: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
