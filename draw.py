#!/usr/bin/env python3
"""Рисует надпись на графике активности GitHub (последние 12 месяцев).

Пересобирает историю этого репозитория: корневой коммит (с файлами) +
N пустых коммитов на каждый «пиксель» надписи с датами в прошлом +
коммит синхронизации, если файлы менялись после корневого.
Запускается раз в неделю, чтобы надпись сдвигалась вместе с окном графика.

Использование: python draw.py <путь к репозиторию>
Переменные окружения: ART_TEXT, ART_EMAIL, ART_NAME, ART_COMMITS, ART_TZ
"""
import os, subprocess, sys
from datetime import date, datetime, timedelta, timezone

TEXT = os.environ.get("ART_TEXT", "RedLine.surf")
EMAIL = os.environ.get("ART_EMAIL", "74730802+Alast0rRL@users.noreply.github.com")
NAME = os.environ.get("ART_NAME", "Alast0rRL")
COMMITS = int(os.environ.get("ART_COMMITS", "20"))   # коммитов на пиксель
TZ_HOURS = int(os.environ.get("ART_TZ", "5"))         # Уфа/Екатеринбург, UTC+5
WEEKS = 53                                            # столбцов в графике

# Шрифт высотой 7 клеток (строка 0 = воскресенье), ширина переменная
FONT = {
 'R':["###.","#..#","#..#","###.","#.#.","#..#","#..#"],
 'e':["....","....",".##.","#..#","####","#...",".###"],
 'd':["...#","...#",".###","#..#","#..#","#..#",".###"],
 'L':["#..","#..","#..","#..","#..","#..","###"],
 'i':["#",".","#","#","#","#","#"],
 'n':["....","....","###.","#..#","#..#","#..#","#..#"],
 '.':[".",".",".",".",".",".","#"],
 's':["....","....",".###","#...",".##.","...#","###."],
 'u':["....","....","#..#","#..#","#..#","#..#",".###"],
 'r':["...","...","#.#","##.","#..","#..","#.."],
 'f':[".##","#..","###","#..","#..","#..","#.."],
 ' ':["..",".." ,"..","..","..","..",".."],
}

def bitmap(text):
    rows = [""] * 7
    for i, ch in enumerate(text):
        g = FONT[ch]
        for r in range(7):
            rows[r] += g[r] + ("." if i < len(text) - 1 else "")
    return rows

def pixel_dates(today):
    rows = bitmap(TEXT)
    width = len(rows[0])
    # Справа оставляем текущую и прошлую неделю пустыми (будущих дат быть не должно),
    # слева — первый, возможно неполный, столбец.
    if width > WEEKS - 3:
        sys.exit(f"Надпись шириной {width} не помещается (максимум {WEEKS - 3})")
    sunday = today - timedelta(days=(today.weekday() + 1) % 7)   # начало текущей недели
    last_col = WEEKS - 3                                         # индекс столбца для правого края
    first_col = last_col - width + 1
    dates = []
    for x in range(width):
        week_start = sunday - timedelta(weeks=(WEEKS - 1) - (first_col + x))
        for r in range(7):
            if rows[r][x] == "#":
                dates.append(week_start + timedelta(days=r))
    return sorted(dates)

def git(*args, env=None, inp=None):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True,
                          env=env, input=inp).stdout.strip()

SYNC_DATE = "2020-11-19T12:00:00+05:00"   # служебные коммиты — вне окна графика

def main():
    repo = sys.argv[1]
    os.chdir(repo)
    tz = timezone(timedelta(hours=TZ_HOURS))
    today = datetime.now(tz).date()
    dates = pixel_dates(today)

    root = git("rev-list", "--max-parents=0", "HEAD").split()[-1]
    root_tree = git("rev-parse", root + "^{tree}")
    head_tree = git("rev-parse", "HEAD^{tree}")

    env = dict(os.environ, GIT_AUTHOR_NAME=NAME, GIT_AUTHOR_EMAIL=EMAIL,
               GIT_COMMITTER_NAME=NAME, GIT_COMMITTER_EMAIL=EMAIL)
    parent = root
    for d in dates:
        for k in range(COMMITS):
            stamp = f"{d.isoformat()}T12:{k // 60:02d}:{k % 60:02d}{TZ_HOURS:+03d}:00"
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = stamp
            parent = git("commit-tree", root_tree, "-p", parent, "-m", "pixel", env=env)
    if head_tree != root_tree:   # сохранить изменения файлов, сделанные после корневого коммита
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = SYNC_DATE
        parent = git("commit-tree", head_tree, "-p", parent, "-m", "sync files", env=env)
    git("update-ref", "HEAD", parent)
    print(f"{len(dates)} пикселей × {COMMITS} = {len(dates) * COMMITS} коммитов, "
          f"с {dates[0]} по {dates[-1]}")

if __name__ == "__main__":
    main()
