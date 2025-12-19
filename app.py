import streamlit as st
import json
import random
import os
import time

# --- 页面配置 ---
st.set_page_config(
    page_title="神经系统复习题库 Pro",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 自定义 CSS ---
st.markdown("""
<style>
    .question-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 5px solid #4e8cff;
    }
    .explanation-box {
        background-color: #e8f5e9;
        padding: 15px;
        border-radius: 5px;
        margin-top: 10px;
        border: 1px solid #c8e6c9;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. 数据与文件管理 ---
DATA_FILE = 'data.json'
USER_DIR = 'user_progress'  # 用户存档文件夹

if not os.path.exists(USER_DIR):
    os.makedirs(USER_DIR)


@st.cache_data
def load_questions():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ 未找到题库文件 data.json")
        return []


raw_data = load_questions()
categories = ["全部"] + sorted(list(set([q["category"] for q in raw_data])))


# --- 2. 用户存档读写函数 ---
def get_user_filename(username):
    return os.path.join(USER_DIR, f"{username}.json")


def save_progress(username):
    """将当前 session_state 中的关键数据保存到文件"""
    if not username: return

    # 将 set 转换为 list 以便 JSON 序列化
    wrong_book_list = list(st.session_state.wrong_book)

    data = {
        "current_index": st.session_state.current_index,
        "score": st.session_state.score,
        "answered_count": st.session_state.answered_count,
        "wrong_book": wrong_book_list,
        "user_answers": st.session_state.user_answers,  # 字典 key是int，json保存后会变str，需注意
        "mode": st.session_state.mode,
        "filtered_indices": st.session_state.filtered_indices,
        "shuffled": st.session_state.shuffled,
        "selected_category": st.session_state.get('selected_category', '全部')
    }

    try:
        with open(get_user_filename(username), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存进度失败: {e}")


def load_progress(username):
    """从文件加载进度到 session_state"""
    filepath = get_user_filename(username)
    if not os.path.exists(filepath):
        return False  # 新用户

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        st.session_state.current_index = data.get("current_index", 0)
        st.session_state.score = data.get("score", 0)
        st.session_state.answered_count = data.get("answered_count", 0)
        # set 还原
        st.session_state.wrong_book = set(data.get("wrong_book", []))
        # 字典 key 还原为 int
        saved_answers = data.get("user_answers", {})
        st.session_state.user_answers = {int(k): v for k, v in saved_answers.items()}

        st.session_state.mode = data.get("mode", 'practice')
        st.session_state.filtered_indices = data.get("filtered_indices", list(range(len(raw_data))))
        st.session_state.shuffled = data.get("shuffled", False)
        st.session_state.selected_category = data.get("selected_category", '全部')
        return True
    except Exception as e:
        st.error(f"读取存档失败: {e}")
        return False


# --- 3. 登录逻辑 (利用 Query Params 保持登录状态) ---
# 获取 URL 中的 user 参数
query_params = st.query_params
url_user = query_params.get("user", "")

if "username" not in st.session_state:
    st.session_state.username = url_user

# 如果没有登录，显示登录界面
if not st.session_state.username:
    st.title("🎓 神经系统刷题 App")
    with st.container():
        st.info("请输入你的昵称开始刷题（系统会自动读取该昵称的存档）")
        name_input = st.text_input("请输入昵称/学号 (例如: alex)", key="login_input")
        if st.button("🚀 开始 / 继续", type="primary"):
            if name_input.strip():
                st.session_state.username = name_input.strip()
                # 更新 URL，这样刷新也不会掉登录
                st.query_params["user"] = st.session_state.username
                st.rerun()
            else:
                st.warning("名字不能为空")
    st.stop()  # 停止执行后续代码，直到登录

# --- 登录后的逻辑 ---
current_user = st.session_state.username

# 首次加载存档 (如果 Session 还没初始化)
if "initialized" not in st.session_state:
    if load_progress(current_user):
        st.toast(f"欢迎回来, {current_user}! 进度已恢复 📂")
    else:
        # 新用户初始化
        st.session_state.current_index = 0
        st.session_state.score = 0
        st.session_state.answered_count = 0
        st.session_state.wrong_book = set()
        st.session_state.user_answers = {}
        st.session_state.mode = 'practice'
        st.session_state.filtered_indices = list(range(len(raw_data)))
        st.session_state.shuffled = False
        st.session_state.selected_category = '全部'
        st.toast(f"你好, {current_user}! 新档案已创建 🆕")

    st.session_state.initialized = True
    st.session_state.show_explanation = False  # 这个状态不需要持久化，每次进来重新做当前题即可

# --- 侧边栏 ---
with st.sidebar:
    st.write(f"👤 当前用户: **{current_user}**")
    if st.button("登出 / 切换账号"):
        st.query_params.clear()  # 清除 URL 参数
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()
    st.header("⚙️ 设置")

    # 模式选择 (这里需要处理一下，因为 selected_category 也可能变)
    mode_options = ["顺序练习", "随机练习", "🔥 错题本重练"]
    # 根据当前 state 决定默认 index
    default_mode_index = 0
    if st.session_state.mode == 'mistake_review':
        default_mode_index = 2
    elif st.session_state.shuffled:
        default_mode_index = 1

    mode = st.radio("模式", mode_options, index=default_mode_index)

    # 只有在非错题模式下显示分类
    selected_cat = st.session_state.get('selected_category', '全部')
    category_index = categories.index(selected_cat) if selected_cat in categories else 0

    new_category = selected_cat
    if mode != "🔥 错题本重练":
        new_category = st.selectbox("章节筛选", categories, index=category_index)

    # 重置/应用按钮
    if st.button("🔄 应用设置 / 重置进度"):
        st.session_state.current_index = 0
        st.session_state.show_explanation = False
        # 不清除分数和错题本，除非是手动要求清空？
        # 为了简单，这里重置"当前列表的进度"，保留总错题本

        all_indices = range(len(raw_data))
        if mode == "🔥 错题本重练":
            st.session_state.filtered_indices = list(st.session_state.wrong_book)
            st.session_state.mode = 'mistake_review'
            if not st.session_state.filtered_indices:
                st.warning("错题本为空！")
        else:
            if new_category == "全部":
                subset = list(all_indices)
            else:
                subset = [i for i in all_indices if raw_data[i]["category"] == new_category]

            st.session_state.filtered_indices = subset
            if mode == "随机练习":
                random.shuffle(st.session_state.filtered_indices)
                st.session_state.shuffled = True
            else:
                st.session_state.filtered_indices.sort()
                st.session_state.shuffled = False
            st.session_state.mode = 'practice'
            st.session_state.selected_category = new_category

        save_progress(current_user)  # 立即保存设置更改
        st.rerun()

    # 数据展示
    st.divider()
    total_q = len(st.session_state.filtered_indices)
    curr_q = st.session_state.current_index + 1 if total_q > 0 else 0
    st.write(f"📊 进度: {curr_q} / {total_q}")
    st.progress(min(curr_q / total_q, 1.0) if total_q > 0 else 0)

    acc = 0
    if st.session_state.answered_count > 0:
        acc = (st.session_state.score / st.session_state.answered_count) * 100
    st.metric("正确率", f"{acc:.1f}%", f"已答 {st.session_state.answered_count} 题")
    st.write(f"📕 错题本: {len(st.session_state.wrong_book)} 题")

# --- 主界面 ---
if len(st.session_state.filtered_indices) > 0:
    if st.session_state.current_index < len(st.session_state.filtered_indices):
        real_idx = st.session_state.filtered_indices[st.session_state.current_index]
        q = raw_data[real_idx]

        st.markdown(f"#### Question {st.session_state.current_index + 1}")
        st.markdown(f"""
        <div class="question-card">
            <span style="color:grey; font-size:0.8em">{q['category']}</span>
            <h3>{q['question']}</h3>
        </div>
        """, unsafe_allow_html=True)

        # 检查是否做过 (回显)
        previous_answer = st.session_state.user_answers.get(real_idx)

        # 表单
        with st.form(key=f"form_{real_idx}"):
            # 如果做过，就锁定或显示之前选的，这里为了简单，做过的题允许重做，或者显示结果
            # Streamlit radio index 必须是 int

            # 查找选项 index
            try:
                prev_idx = q['options'].index(previous_answer) if previous_answer else None
            except:
                prev_idx = None

            choice = st.radio(
                "请选择:",
                q['options'],
                index=prev_idx if prev_idx is not None else 0,
                disabled=st.session_state.show_explanation  # 提交后锁定
            )

            # 按钮状态
            btn_text = "提交答案" if not st.session_state.show_explanation else "已提交"
            submit = st.form_submit_button(btn_text, type="primary", disabled=st.session_state.show_explanation)

            if submit:
                st.session_state.show_explanation = True
                st.session_state.user_answers[real_idx] = choice

                if choice == q['answer']:
                    # 只有第一次做对才加分（防止刷分）
                    # 简化逻辑：只要做对就加分，但总题数也增加
                    st.session_state.score += 1
                    # 如果在错题本模式做对了，可以将它移出错题本吗？
                    # 可以在这里加个逻辑：
                    if st.session_state.mode == 'mistake_review' and real_idx in st.session_state.wrong_book:
                        st.session_state.wrong_book.remove(real_idx)
                        st.toast("已将此题移出错题本！🎉")
                else:
                    st.session_state.wrong_book.add(real_idx)

                st.session_state.answered_count += 1

                # 🔥 关键：每次交互后保存到文件
                save_progress(current_user)
                st.rerun()

        # 显示解析
        if st.session_state.show_explanation or previous_answer:
            # 重新获取用户当前选的（因为 rerun 后 choice 变量范围问题，直接从 session 取最稳）
            my_ans = st.session_state.user_answers.get(real_idx, choice)

            if my_ans == q['answer']:
                st.success("✅ 回答正确！")
            else:
                st.error(f"❌ 回答错误！你选的是：{my_ans}")

            st.info(f"👉 正确答案：**{q['answer']}**")
            with st.expander("查看详细解析", expanded=True):
                st.markdown(f'<div class="explanation-box">{q["explanation"]}</div>', unsafe_allow_html=True)

            # 下一题按钮
            col1, col2 = st.columns([4, 1])
            with col2:
                if st.button("下一题 ➡️"):
                    st.session_state.current_index += 1
                    st.session_state.show_explanation = False
                    save_progress(current_user)  # 索引变了也要存
                    st.rerun()

    else:
        st.balloons()
        st.success("🎉 当前列表的所有题目已完成！")
        if st.button("再来一轮"):
            st.session_state.current_index = 0
            st.session_state.show_explanation = False
            save_progress(current_user)
            st.rerun()
else:
    st.warning("当前列表为空。请在侧边栏调整筛选条件（例如：如果是在错题模式，可能你已经消灭了所有错题！）。")