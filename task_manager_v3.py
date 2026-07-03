# -*- coding: utf-8 -*-
"""
ADHD友好任务清单 v3
在 v2.1 基础上新增：
  🛡 地基：每次操作后随手保存（直接关窗口也不丢）、原子写入+自动备份(.bak)、
          输入容错（输错不再崩溃）、visible_tasks() 统一管理屏幕序号
  🗑 放弃任务（无愧疚清理） / ✏ 编辑任务
  🎲 "现在干嘛"：程序随机替你挑一件，对抗决策瘫痪
  🟦 次数进度条 + 🔥 连续打卡streak（只庆祝，不惩罚：断签不警告，重新数就是）
"""

import json
import os
import random
import sys
from datetime import date, timedelta

# Windows的cmd默认用GBK编码，打印emoji会直接崩溃；这里强制输出走UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass   # 很老的Python没有reconfigure，就算了

# 数据文件固定放在本py文件旁边，不管从哪个目录启动（CLI和网页版共用同一份数据）
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")
CATEGORIES = {"1": "日常", "2": "近期", "3": "兴趣"}   # 类别翻译表，add和edit共用


# ---------- 日期 ----------

def today_str():
    return date.today().isoformat()          # 例如 '2026-07-03'


def yesterday_str():
    return (date.today() - timedelta(days=1)).isoformat()


# ---------- 数据读写 ----------

def load_tasks():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasks(tasks):
    """原子保存：先写临时文件再一步替换，中途被杀也不会留下写了一半的坏文件；
    上一版数据留作 .bak 备份，万一手滑还能救回来"""
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    if os.path.exists(DATA_FILE):
        os.replace(DATA_FILE, DATA_FILE + ".bak")
    os.replace(tmp, DATA_FILE)               # os.replace 在操作系统层面是原子的


def fix_old_tasks(tasks):
    """数据迁移：给旧版本创建的任务补上新字段。
    setdefault：键不存在才写入默认值，存在就不动"""
    for t in tasks:
        t.setdefault("last_done", "")        # 最后一次打卡的日期
        t.setdefault("times", 1)             # 每天目标次数
        t.setdefault("left", 0 if t["done"] else 1)   # 今天还剩几次
        t.setdefault("streak", 0)            # 连续做满的天数
        t.setdefault("last_full", "")        # 最后一次"做满"的日期，streak靠它判断


def reset_daily_tasks(tasks):
    """启动时调用：日常任务只要不是"今天"做过的，就复原并把次数回满"""
    for t in tasks:
        if t["category"] == "日常" and t["last_done"] != today_str():
            t["done"] = False
            t["left"] = t["times"]


# ---------- 输入容错 ----------

def ask_int(prompt, default=None):
    """要一个整数：输的不是数字就重问，绝不崩溃；
    直接回车且给了default时返回default"""
    while True:
        raw = input(prompt).strip()
        if raw == "" and default is not None:
            return default
        try:
            return int(raw)
        except ValueError:
            print("❌ 请输入数字")


# ---------- 可见列表（所有功能共用的唯一顺序来源） ----------

def visible_tasks(tasks):
    """返回"屏幕上按序号排列的待办任务"。
    list/打卡/编辑/放弃/随机抽 全部基于它，序号永远对得上"""
    daily = [t for t in tasks if not t["done"] and t["category"] == "日常"]
    other = [t for t in tasks if not t["done"] and t["category"] != "日常"]
    other.sort(key=lambda t: t["priority"])
    return daily + other


def pick_from_visible(tasks, action_word):
    """显示列表→让用户选序号→返回选中的任务；取消或无效返回None。
    打卡/编辑/放弃三个功能共用，不再各写一遍"""
    if not visible_tasks(tasks):
        print("没有待办任务")
        return None
    list_tasks(tasks)
    num = ask_int(f"{action_word}哪个？输入序号（直接回车取消）：", default=-1)
    vis = visible_tasks(tasks)
    if num < 0 or num >= len(vis):
        if num != -1:
            print("❌ 序号不存在")
        return None
    return vis[num]


# ---------- 显示 ----------

def progress_bar(t):
    """次数任务的进度条，例如 🟦🟦🟦⬜⬜⬜⬜⬜ 3/8"""
    done_times = t["times"] - t["left"]
    return "🟦" * done_times + "⬜" * t["left"] + f" {done_times}/{t['times']}"


def list_tasks(tasks):
    vis = visible_tasks(tasks)
    daily = [t for t in vis if t["category"] == "日常"]
    other = [t for t in vis if t["category"] != "日常"]
    daily_done = [t for t in tasks if t["done"] and t["category"] == "日常"]

    if not vis:
        print("🎉 全部完成！去玩吧！")
        for t in daily_done:
            fire = f" 🔥×{t['streak']}" if t["streak"] >= 2 else ""
            print(f"   ✅ {t['name']}{fire}")
        return

    print("\n" + "=" * 30)

    print(f"🔴 今日日常（还剩{len(daily)}件）")
    idx = 0
    for t in daily:
        # 昨天做满了、今天还没做完 → 提示连击待续，制造"别断"的正向动力
        fire = f"  🔥{t['streak']}天连击中" if t["streak"] >= 2 and t["last_full"] == yesterday_str() else ""
        bar = f"  {progress_bar(t)}" if t["times"] > 1 else ""
        print(f"   [{idx}] {t['name']}{bar}{fire}")
        idx += 1
    for t in daily_done:
        fire = f" 🔥×{t['streak']}" if t["streak"] >= 2 else ""
        print(f"   ✅ {t['name']}{fire}")

    print("-" * 30)

    print("📌 近期 & 💡 兴趣")
    for t in other:
        mark = "🎯" if t["priority"] == 1 else ("💡" if t["category"] == "兴趣" else "  ")
        print(f"{mark} [{idx}] {t['name']}")
        idx += 1
    print("=" * 30)


# ---------- 添加 ----------

def add_task(tasks):
    name = input("任务名称：").strip()
    if not name:
        print("❌ 名称不能为空")
        return

    cat_choice = input("类别（1=日常/2=近期/3=兴趣）：").strip()
    category = CATEGORIES.get(cat_choice, "近期")

    priority = ask_int("优先级（1=优先/2=普通/3=可推迟，回车=2）：", default=2)

    if category == "日常":
        times = ask_int("每天要做几次？（回车=8次，适合喝水这类）：", default=8)
    else:
        times = 1

    tasks.append(new_task(name, category, priority, times))
    print(f"✅ 已添加到【{category}】：{name}")


def new_task(name, category, priority, times):
    """任务字典的唯一出生地：CLI和网页版共用，字段改这里一处就够"""
    return {
        "name": name,
        "category": category,
        "priority": priority,
        "times": times,
        "left": times,
        "done": False,
        "last_done": "",
        "streak": 0,
        "last_full": "",
    }


# ---------- 打卡 ----------

def check_in(t):
    """打卡一次；减到0才算今天完成。返回结果消息——CLI打印它，网页版展示它"""
    t["left"] -= 1
    t["last_done"] = today_str()

    if t["left"] > 0:
        msg = f"👍 {t['name']} +1  {progress_bar(t)}"
        print(msg)
        return msg

    t["done"] = True
    if t["category"] == "日常":
        # streak规则：昨天也做满了就+1，否则从1重新数（不警告不指责）
        if t["last_full"] == yesterday_str():
            t["streak"] += 1
        else:
            t["streak"] = 1
        t["last_full"] = today_str()
        fire = f"  🔥连续{t['streak']}天！" if t["streak"] >= 2 else ""
        msg = f"✅ 完成：{t['name']}，干得漂亮！{fire}"
    else:
        msg = f"✅ 完成：{t['name']}，干得漂亮！"
    print(msg)
    return msg


def complete_task(tasks):
    t = pick_from_visible(tasks, "打卡")
    if t:
        check_in(t)


# ---------- 🎲 现在干嘛 ----------

def pick_for_me(tasks):
    """决策瘫痪救星：程序替你挑一件。日常没清完就先从日常里抽"""
    vis = visible_tasks(tasks)
    if not vis:
        print("🎉 没有待办任务，去玩吧！")
        return
    daily = [t for t in vis if t["category"] == "日常"]
    pool = daily if daily else vis
    t = random.choice(pool)
    print(f"\n🎲 就它了 →  {t['name']}")
    ans = input("做完回来按 y 打卡（回车=先返回菜单）：").strip().lower()
    if ans == "y":
        check_in(t)


# ---------- 编辑 / 放弃 ----------

def edit_task(tasks):
    t = pick_from_visible(tasks, "编辑")
    if t is None:
        return

    # 每一项直接回车 = 保持原值
    new_name = input(f"名称（回车保持「{t['name']}」）：").strip()
    if new_name:
        t["name"] = new_name

    cat_choice = input(f"类别 1=日常/2=近期/3=兴趣（回车保持「{t['category']}」）：").strip()
    if cat_choice in CATEGORIES:
        t["category"] = CATEGORIES[cat_choice]

    t["priority"] = ask_int(f"优先级 1=优先/2=普通/3=可推迟（回车保持{t['priority']}）：",
                            default=t["priority"])

    if t["category"] == "日常":
        new_times = ask_int(f"每天几次（回车保持{t['times']}）：", default=t["times"])
        if new_times != t["times"]:
            done_times = t["times"] - t["left"]      # 今天已经做掉的次数不作废
            t["times"] = new_times
            t["left"] = max(new_times - done_times, 0)
            if t["left"] == 0:
                t["done"] = True

    print(f"✏ 已更新：{t['name']}")


def drop_task(tasks):
    t = pick_from_visible(tasks, "放弃")
    if t is None:
        return
    sure = input(f"确定放弃「{t['name']}」？(y=确定/回车=取消)：").strip().lower()
    if sure == "y":
        tasks.remove(t)
        print(f"🗑 已放弃：{t['name']}。放弃也是决策，给大脑腾地方 👍")


# ---------- 主程序 ----------

def main():
    tasks = load_tasks()
    fix_old_tasks(tasks)       # 先补齐旧任务缺的字段
    reset_daily_tasks(tasks)   # 再重置过期的日常任务（顺序不能反）
    save_tasks(tasks)          # 启动时的重置结果立刻落盘

    print("=" * 30)
    print("📋 我的任务清单")
    list_tasks(tasks)

    while True:
        print("\n1.添加  2.查看  3.打卡  4.现在干嘛🎲  5.编辑  6.放弃  0.退出")
        choice = input("选择操作：").strip()

        if choice == "1":
            add_task(tasks)
        elif choice == "2":
            list_tasks(tasks)
        elif choice == "3":
            complete_task(tasks)
        elif choice == "4":
            pick_for_me(tasks)
        elif choice == "5":
            edit_task(tasks)
        elif choice == "6":
            drop_task(tasks)
        elif choice == "0":
            print("已保存，明天见 👋")
            break
        else:
            print("请输入菜单里的数字")
            continue

        save_tasks(tasks)      # 🛡 每次操作后随手保存，直接关窗口也不丢数据


if __name__ == "__main__":
    main()
