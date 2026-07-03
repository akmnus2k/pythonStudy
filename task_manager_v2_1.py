# -*- coding: utf-8 -*-
"""
ADHD友好任务清单 v2.1 - 日常任务每日重置 + 次数打卡
所有和v2（test2.py）不同的地方都标了 🆕
新思路：
  1. 做任务时记下"哪天做的"（last_done）；启动时发现不是今天，日常任务自动复原
  2. 日常任务可以设每天次数（比如喝水8次），做一次减一次，减到0才算完成
  3. 去掉了"预计分钟数"——对ADHD来说估时意义不大，反而增加添加任务的负担
旧的 tasks.json 不用删：fix_old_tasks() 会自动给旧任务补上缺的字段
"""

import json
import os
from datetime import date         # 🆕 标准库里的日期工具，date.today()能拿到今天


DATA_FILE = "tasks.json"


# ---------- 数据读写（这部分完全没变） ----------

def load_tasks():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasks(tasks):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


# ---------- 🆕 兼容旧数据 + 日常任务每日重置 ----------

def today_str():
    """🆕 返回今天的日期字符串，例如 '2026-07-03'（方便和last_done直接比较）"""
    return date.today().isoformat()


def fix_old_tasks(tasks):
    """🆕 给旧版本创建的任务补上新字段，防止KeyError（这个过程叫"数据迁移"）"""
    for t in tasks:
        if "last_done" not in t:           # in 可以检查字典里有没有某个键
            t["last_done"] = ""
        if "times" not in t:
            t["times"] = 1                 # 旧任务默认每天只做1次
        if "left" not in t:
            t["left"] = 0 if t["done"] else 1


def reset_daily_tasks(tasks):
    """🆕 启动时调用：日常任务只要不是"今天"做过的，就整个复原"""
    for t in tasks:
        if t["category"] == "日常" and t["last_done"] != today_str():
            t["done"] = False
            t["left"] = t["times"]         # 剩余次数回满：昨天喝了3次不算，今天重新数


# ---------- 添加任务 ----------

def add_task(tasks):
    name = input("任务名称：")

    cat_choice = input("类别（1=日常/2=近期/3=兴趣）：")
    categories = {"1": "日常", "2": "近期", "3": "兴趣"}
    category = categories.get(cat_choice, "近期")

    priority = int(input("优先级（1=优先/2=普通/3=可推迟）："))   # 🆕 改了提示文字

    # 🆕 只有日常任务才问次数；近期/兴趣做一次就算完
    if category == "日常":
        times_input = input("每天要做几次？（直接回车=8次，适合喝水这类）：")
        # 🆕 条件表达式：输入了就转成数字，直接回车（空字符串）就用默认值8
        times = int(times_input) if times_input != "" else 8
    else:
        times = 1

    task = {
        "name": name,
        "category": category,
        "priority": priority,
        "times": times,            # 🆕 每天目标次数
        "left": times,             # 🆕 今天还剩几次，做一次减一
        "done": False,
        "last_done": "",           # 🆕 最后一次做的日期，还没做过就是空字符串
    }
    tasks.append(task)
    print(f"✅ 已添加到【{category}】：{name}")


# ---------- 查看今日任务 ----------

def list_tasks(tasks):
    daily = [t for t in tasks if not t["done"] and t["category"] == "日常"]
    other = [t for t in tasks if not t["done"] and t["category"] != "日常"]

    daily_done = [t for t in tasks if t["done"] and t["category"] == "日常"]

    if len(daily) == 0 and len(other) == 0:
        print("🎉 全部完成！去玩吧！")
        return

    print("\n" + "=" * 30)

    print(f"🔴 今日日常（还剩{len(daily)}件）")
    idx = 0
    for t in daily:
        # 🆕 一天要做多次的任务，把剩余次数显示出来
        if t["times"] > 1:
            print(f"   [{idx}] {t['name']}（还剩{t['left']}次）")
        else:
            print(f"   [{idx}] {t['name']}")
        idx += 1
    for t in daily_done:
        print(f"   ✅ {t['name']}")

    print("-" * 30)

    print("📌 近期 & 💡 兴趣")
    other = sorted(other, key=lambda t: t["priority"])
    for t in other:
        mark = "🎯" if t["priority"] == 1 else ("💡" if t["category"] == "兴趣" else "  ")
        print(f"{mark} [{idx}] {t['name']}")     # 🆕 去掉了"(x分钟)"
        idx += 1
    print("=" * 30)


# ---------- 完成任务 ----------

def complete_task(tasks):
    # 这里拼接列表的顺序必须和 list_tasks 显示的顺序完全一致
    daily = [t for t in tasks if not t["done"] and t["category"] == "日常"]
    other = [t for t in tasks if not t["done"] and t["category"] != "日常"]
    other = sorted(other, key=lambda t: t["priority"])
    visible = daily + other

    if len(visible) == 0:
        print("没有待办任务")
        return

    list_tasks(tasks)
    num = int(input("完成哪个任务？输入序号："))

    if num < 0 or num >= len(visible):
        print("❌ 序号不存在")
        return

    t = visible[num]                  # 🆕 先存进短变量，下面写起来清爽
    t["left"] = t["left"] - 1         # 🆕 做一次减一次
    t["last_done"] = today_str()      # 🆕 每打卡一次都记日期，明天启动时靠它判断要不要重置

    if t["left"] <= 0:                # 🆕 减到0，今天才算真正完成
        t["done"] = True
        print(f"✅ 完成：{t['name']}，干得漂亮！")
    else:
        print(f"👍 {t['name']} +1，今天还剩 {t['left']} 次")


# ---------- 主程序 ----------

def main():
    tasks = load_tasks()
    fix_old_tasks(tasks)       # 🆕 第一步：给旧任务补齐新字段
    reset_daily_tasks(tasks)   # 🆕 第二步：过期的日常任务复原（顺序不能反，想想为什么）
    print("=" * 30)
    print("📋 我的任务清单")
    list_tasks(tasks)

    while True:
        print("\n1.添加任务  2.查看今日  3.完成任务  4.退出")
        choice = input("选择操作：")

        if choice == "1":
            add_task(tasks)
        elif choice == "2":
            list_tasks(tasks)
        elif choice == "3":
            complete_task(tasks)
        elif choice == "4":
            save_tasks(tasks)
            print("已保存，明天见 👋")
            break
        else:
            print("请输入 1-4")


if __name__ == "__main__":
    main()
