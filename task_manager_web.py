# -*- coding: utf-8 -*-
"""
ADHD友好任务清单 - 网页版
运行方式：streamlit run task_manager_web.py
架构：本文件只负责"界面"，所有业务逻辑复用 task_manager_v3.py（逻辑层）
Streamlit的运行模型：每次点击任何按钮，整个脚本从第1行重新跑一遍——
所以没有while循环，状态靠 tasks.json（持久数据）和 st.session_state（临时数据）保存
"""

import random

import streamlit as st

import task_manager_v3 as core   # v3是逻辑层：读写/重置/打卡/排序全在里面

st.set_page_config(page_title="我的任务清单", page_icon="📋", layout="centered")

# 主题的浅蓝主色上，Streamlit默认的白色按钮文字看不清，改成深蓝灰
st.markdown("""
<style>
button[kind="primary"] p { color: #2C4A5E !important; }
</style>
""", unsafe_allow_html=True)

PRIORITY_NAMES = {1: "优先", 2: "普通", 3: "可推迟"}


# ---------- 每次重跑都执行：读数据 + 日常重置 ----------

tasks = core.load_tasks()
core.fix_old_tasks(tasks)
core.reset_daily_tasks(tasks)
core.save_tasks(tasks)


# ---------- 闪存消息：跨越一次重跑传递提示文字 ----------

def flash(msg):
    """先把消息存进session_state，rerun之后再显示（直接st.success会被重跑冲掉）"""
    st.session_state["flash"] = msg


def do(t, action_msg):
    """所有按钮的统一收尾：存消息→写盘→重跑刷新界面"""
    flash(action_msg)
    core.save_tasks(tasks)
    st.rerun()


if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))   # pop：显示一次就删，避免常驻


# ---------- 侧边栏：添加任务 ----------

with st.sidebar:
    st.header("➕ 添加任务")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("任务名称")
        category = st.radio("类别", ["日常", "近期", "兴趣"], horizontal=True)
        priority = st.selectbox("优先级", [1, 2, 3], index=1,
                                format_func=lambda p: PRIORITY_NAMES[p])
        times = st.number_input("每天几次（只对日常生效）", 1, 50, 8)
        if st.form_submit_button("添加", use_container_width=True):
            if not name.strip():
                st.error("名称不能为空")
            else:
                if category != "日常":
                    times = 1                    # 近期/兴趣做一次就算完
                tasks.append(core.new_task(name.strip(), category, priority, int(times)))
                do(None, f"✅ 已添加到【{category}】：{name.strip()}")


# ---------- 主区 ----------

st.title("📋 我的任务清单")

vis = core.visible_tasks(tasks)
daily = [t for t in vis if t["category"] == "日常"]
other = [t for t in vis if t["category"] != "日常"]
daily_done = [t for t in tasks if t["done"] and t["category"] == "日常"]

# 🎲 现在干嘛：置顶大按钮，决策瘫痪时按它
if st.button("🎲 现在干嘛？", type="primary", use_container_width=True, disabled=not vis):
    pool = daily if daily else vis               # 日常没清完就先从日常里抽
    st.session_state["pick"] = tasks.index(random.choice(pool))

pick = st.session_state.get("pick")
if pick is not None:
    # 防御：重跑之间任务可能被删/完成，序号可能失效
    if pick >= len(tasks) or tasks[pick]["done"]:
        st.session_state.pop("pick")
    else:
        t = tasks[pick]
        c1, c2 = st.columns([4, 1])
        c1.info(f"🎲 就它了 → **{t['name']}**")
        if c2.button("✅ 打卡", key="pick_checkin", use_container_width=True):
            msg = core.check_in(t)
            if t["done"]:
                st.session_state.pop("pick", None)
            do(t, msg)

if not vis:
    st.success("🎉 全部完成！去玩吧！")
    if st.session_state.pop("just_done", False):
        st.balloons()                            # 清空全部任务的瞬间放个气球，多巴胺+1


def task_row(t, label):
    """渲染一行任务：名字/进度条 + 打卡按钮 + 🗑放弃（带确认）"""
    i = tasks.index(t)                           # 用在tasks里的位置当按钮的唯一key
    c1, c2, c3 = st.columns([6, 2, 1])

    fire = ""
    if t["streak"] >= 2 and t["last_full"] == core.yesterday_str():
        fire = f" &nbsp;🔥{t['streak']}天连击中"
    c1.markdown(f"{label}**{t['name']}**{fire}")
    if t["times"] > 1:
        done_times = t["times"] - t["left"]
        c1.progress(done_times / t["times"], text=f"{done_times}/{t['times']}")

    if c2.button("打卡", key=f"checkin_{i}", use_container_width=True):
        msg = core.check_in(t)
        if t["done"]:
            st.session_state["just_done"] = True
        do(t, msg)

    with c3.popover("🗑"):                       # 放弃是唯一不可逆操作，弹窗二次确认
        st.write(f"确定放弃「{t['name']}」？")
        if st.button("确定放弃", key=f"drop_{i}", type="primary"):
            tasks.remove(t)
            do(None, f"🗑 已放弃：{t['name']}。放弃也是决策，给大脑腾地方 👍")


if daily or daily_done:
    st.subheader(f"💙 今日日常（还剩{len(daily)}件）")
    for t in daily:
        task_row(t, "")
    for t in daily_done:
        fire = f" 🔥×{t['streak']}" if t["streak"] >= 2 else ""
        st.markdown(f"✅ ~~{t['name']}~~{fire}")

if other:
    st.subheader("📌 近期 & 💡 兴趣")
    for t in other:
        mark = "🎯 " if t["priority"] == 1 else ("💡 " if t["category"] == "兴趣" else "")
        task_row(t, mark)
