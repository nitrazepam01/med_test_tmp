import streamlit as st
import json
import random
import os

# --- 页面配置 ---
st.set_page_config(
    page_title="神经系统复习题库",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 自定义 CSS (美化界面) ---
st.markdown("""
<style>
    .stRadio > label {font-size: 1.1rem; font-weight: 500;}
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
    /* 隐藏部分默认装饰 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --- 1. 数据加载与处理 ---
@st.cache_data
def load_data():
    try:
        # 尝试读取本地文件
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error("未找到 data.json 文件，请确保文件在同一目录下。")
        return []


raw_data = load_data()

# 提取所有分类
categories = ["全部"] + sorted(list(set([q["category"] for q in raw_data])))

# --- 2. Session State 初始化 (状态管理) ---
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'answered_count' not in st.session_state:
    st.session_state.answered_count = 0
if 'wrong_book' not in st.session_state:
    st.session_state.wrong_book = set()  # 存储错题的index
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}  # 记录用户的选择 {question_index: option}
if 'show_explanation' not in st.session_state:
    st.session_state.show_explanation = False
if 'mode' not in st.session_state:
    st.session_state.mode = 'practice'  # practice, mistake_review
if 'filtered_indices' not in st.session_state:
    st.session_state.filtered_indices = list(range(len(raw_data)))
if 'shuffled' not in st.session_state:
    st.session_state.shuffled = False

# --- 3. 侧边栏控制区 ---
with st.sidebar:
    st.header("⚙️ 设置与进度")

    # 模式选择
    mode = st.radio("选择模式", ["顺序练习", "随机练习", "🔥 错题本重练"], index=0)

    # 逻辑处理：当模式改变时重置索引
    current_mode_key = 'practice' if mode != "🔥 错题本重练" else 'mistake_review'

    # 分类筛选 (仅在非错题模式下显示)
    selected_category = "全部"
    if current_mode_key == 'practice':
        selected_category = st.selectbox("选择章节/分类", categories)


    # 重置/初始化逻辑
    def reset_quiz():
        st.session_state.current_index = 0
        st.session_state.show_explanation = False
        st.session_state.answered_count = 0
        st.session_state.score = 0
        st.session_state.user_answers = {}

        # 筛选题目索引
        all_indices = range(len(raw_data))

        if mode == "🔥 错题本重练":
            st.session_state.filtered_indices = list(st.session_state.wrong_book)
            st.session_state.mode = 'mistake_review'
        else:
            if selected_category == "全部":
                st.session_state.filtered_indices = list(all_indices)
            else:
                st.session_state.filtered_indices = [i for i in all_indices if
                                                     raw_data[i]["category"] == selected_category]

            if mode == "随机练习":
                random.shuffle(st.session_state.filtered_indices)
            else:
                st.session_state.filtered_indices.sort()  # 恢复顺序

            st.session_state.mode = 'practice'


    # 只有当筛选条件变化时才重置，利用button手动重置或检测变化
    if st.button("🔄 重置/应用设置"):
        reset_quiz()
        st.rerun()

    # 如果是第一次运行，自动初始化
    if 'initialized' not in st.session_state:
        reset_quiz()
        st.session_state.initialized = True

    st.divider()

    # 进度展示
    total_q = len(st.session_state.filtered_indices)
    if total_q > 0:
        current_display = st.session_state.current_index + 1
        progress = st.session_state.current_index / total_q
        st.progress(progress)
        st.caption(f"进度: {current_display} / {total_q}")

        if st.session_state.answered_count > 0:
            accuracy = (st.session_state.score / st.session_state.answered_count) * 100
            st.metric("当前正确率", f"{accuracy:.1f}%")

        st.write(f"📖 错题本数量: {len(st.session_state.wrong_book)}")
    else:
        st.warning("当前列表没有题目 (如果是错题本模式，说明你太强了没有错题！)")

# --- 4. 主界面逻辑 ---

# 确保有题可做
if len(st.session_state.filtered_indices) > 0 and st.session_state.current_index < len(
        st.session_state.filtered_indices):

    # 获取真实数据索引
    real_index = st.session_state.filtered_indices[st.session_state.current_index]
    q_data = raw_data[real_index]

    # 题目展示卡片
    st.markdown(f"""
    <div class="question-card">
        <h4>{st.session_state.current_index + 1}. [{q_data['category']}]</h4>
        <h3>{q_data['question']}</h3>
    </div>
    """, unsafe_allow_html=True)

    # 选项表单
    with st.form(key=f"q_form_{real_index}"):
        # 使用Radio button
        user_choice = st.radio("请选择答案:", q_data['options'], key=f"radio_{real_index}")

        # 提交按钮
        submitted = st.form_submit_button("提交答案", type="primary")

        if submitted:
            st.session_state.show_explanation = True

            # 记录是否正确
            if user_choice == q_data['answer']:
                if real_index not in st.session_state.user_answers:  # 防止重复计分
                    st.session_state.score += 1
                # 如果答对了，且之前在错题本里，可以选择移除（可选功能，这里暂时保留不移除，便于复习）
            else:
                st.session_state.wrong_book.add(real_index)  # 加入错题本

            st.session_state.answered_count += 1
            st.session_state.user_answers[real_index] = user_choice
            st.rerun()

    # --- 5. 反馈与解析区域 ---
    if st.session_state.show_explanation:
        correct_answer = q_data['answer']
        # 获取用户刚才选的（从session state或者刚才的变量）
        # 注意：Streamlit rerun后 user_choice 变量可能丢失，最好重新获取或依赖逻辑
        # 但由于form提交后立刻rerun，我们需要在rerun前处理逻辑，或者在rerun后根据状态显示

        # 简单的回显逻辑：如果当前题目在已答记录里
        if real_index in st.session_state.user_answers:
            my_ans = st.session_state.user_answers[real_index]

            if my_ans == correct_answer:
                st.success(f"✅ 回答正确！")
            else:
                st.error(f"❌ 回答错误！你选了：{my_ans}")

            st.info(f"👉 正确答案：**{correct_answer}**")

            with st.expander("查看详细解析", expanded=True):
                st.markdown(f"""
                <div class="explanation-box">
                    <b>💡 解析：</b><br>
                    {q_data['explanation']}
                </div>
                """, unsafe_allow_html=True)

    # --- 6. 翻页控制 ---
    col1, col2 = st.columns([1, 4])
    with col2:
        if st.session_state.show_explanation:  # 只有提交后才显示下一题按钮
            if st.button("下一题 ➡️", type="primary"):
                if st.session_state.current_index < len(st.session_state.filtered_indices) - 1:
                    st.session_state.current_index += 1
                    st.session_state.show_explanation = False
                    st.rerun()
                else:
                    st.balloons()
                    st.success("🎉 恭喜！当前列表题目已全部完成！")
                    if st.button("重新开始"):
                        reset_quiz()
                        st.rerun()

elif len(st.session_state.filtered_indices) == 0:
    st.info("👋 当前没有题目。请在侧边栏调整设置或重置进度。")
    if mode == "🔥 错题本重练":
        st.success("太棒了！你的错题本是空的。")

else:
    st.success("🎉 这一组题目已经做完了！")
    if st.button("重新开始一组"):
        reset_quiz()
        st.rerun()