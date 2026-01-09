#!/usr/bin/env python3
"""
Скрипт для просмотра и удаления зависших транскрипций.

Использование:
    # Показать зависшие (PROCESSING/DIARIZING):
    python dev/cleanup_stuck.py

    # Удалить конкретную по ID:
    python dev/cleanup_stuck.py --delete <id>

    # Удалить ВСЕ зависшие:
    python dev/cleanup_stuck.py --delete-all
"""

import argparse
import sqlite3
from pathlib import Path
from datetime import datetime


def get_db_connection():
    db_path = Path.home() / ".transcribeflow" / "transcribeflow.db"
    if not db_path.exists():
        print(f"База данных не найдена: {db_path}")
        exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def list_stuck(conn):
    """Показать все зависшие транскрипции."""
    cur = conn.cursor()

    # PROCESSING, DIARIZING, QUEUED - все что не COMPLETED/FAILED/DRAFT
    cur.execute("""
        SELECT id, filename, status, progress, created_at, engine, model
        FROM transcriptions
        WHERE status IN ('PROCESSING', 'DIARIZING', 'QUEUED')
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    if not rows:
        print("Зависших транскрипций не найдено.")
        return []

    print(f"Найдено {len(rows)} зависших транскрипций:\n")
    print("-" * 80)

    for row in rows:
        created = datetime.fromisoformat(row['created_at'])
        age = datetime.now() - created
        hours = age.total_seconds() / 3600

        print(f"ID: {row['id']}")
        print(f"  Файл: {row['filename']}")
        print(f"  Статус: {row['status']} ({row['progress']:.0f}%)")
        print(f"  Engine: {row['engine']}/{row['model']}")
        print(f"  Создан: {created.strftime('%Y-%m-%d %H:%M')} ({hours:.1f}ч назад)")
        print("-" * 80)

    return rows


def delete_by_id(conn, transcription_id: str):
    """Удалить транскрипцию по ID."""
    cur = conn.cursor()

    # Проверим что запись существует
    cur.execute("SELECT filename, status FROM transcriptions WHERE id = ?", (transcription_id,))
    row = cur.fetchone()

    if not row:
        print(f"Запись с ID {transcription_id} не найдена.")
        return False

    print(f"Удаление: {row['filename']} ({row['status']})")

    cur.execute("DELETE FROM transcriptions WHERE id = ?", (transcription_id,))
    conn.commit()

    print(f"Удалено: {cur.rowcount} запись")
    return True


def delete_all_stuck(conn):
    """Удалить все зависшие транскрипции."""
    cur = conn.cursor()

    # Сначала покажем что будем удалять
    cur.execute("""
        SELECT COUNT(*) as cnt FROM transcriptions
        WHERE status IN ('PROCESSING', 'DIARIZING')
    """)
    count = cur.fetchone()['cnt']

    if count == 0:
        print("Нечего удалять - зависших транскрипций нет.")
        return

    print(f"Будет удалено {count} записей в статусе PROCESSING/DIARIZING.")
    confirm = input("Подтвердите удаление (yes/no): ")

    if confirm.lower() != 'yes':
        print("Отменено.")
        return

    cur.execute("""
        DELETE FROM transcriptions
        WHERE status IN ('PROCESSING', 'DIARIZING')
    """)
    conn.commit()

    print(f"Удалено: {cur.rowcount} записей")


def main():
    parser = argparse.ArgumentParser(description="Управление зависшими транскрипциями")
    parser.add_argument("--delete", metavar="ID", help="Удалить транскрипцию по ID")
    parser.add_argument("--delete-all", action="store_true", help="Удалить все зависшие")

    args = parser.parse_args()

    conn = get_db_connection()

    try:
        if args.delete:
            delete_by_id(conn, args.delete)
        elif args.delete_all:
            delete_all_stuck(conn)
        else:
            list_stuck(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
