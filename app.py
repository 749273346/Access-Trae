import streamlit as st
import streamlit.components.v1 as components
import os
import sys
import time
from dotenv import load_dotenv

# Add current directory to path to import src modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.clipper import VideoClipper
from src.refinery import ContentRefinery
from src.storage import StorageManager

# Load env variables
load_dotenv()

st.set_page_config(
    page_title="Trae Omni-Browser",
    page_icon="�",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Session State
if 'current_url' not in st.session_state:
    st.session_state.current_url = "https://www.douyin.com"
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'last_saved_file' not in st.session_state:
    st.session_state.last_saved_file = None

# Custom CSS for Browser Look
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    iframe { border: 1px solid #333; border-radius: 8px; }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- Top Navigation Bar ---
col_url, col_go, col_analyze = st.columns([8, 1, 2])

with col_url:
    url_input = st.text_input("Address Bar", value=st.session_state.current_url, label_visibility="collapsed", placeholder="Enter URL (e.g. https://www.douyin.com)")

with col_go:
    if st.button("Go ➡️"):
        st.session_state.current_url = url_input
        st.rerun()

with col_analyze:
    analyze_btn = st.button("✨ Analyze & Clip", type="primary", help="Extract content from this page")

# --- Main Interface ---
col_browser, col_assistant = st.columns([2, 1])

# Left Column: The Browser
with col_browser:
    if st.session_state.current_url:
        try:
            # Use Streamlit's iframe component
            # Note: Some sites (like Google/GitHub) block embedding via X-Frame-Options.
            # Douyin/Bilibili/YouTube embeds usually work or require specific embed URLs.
            # For a general "Browser" feel, we do our best.
            components.iframe(st.session_state.current_url, height=800, scrolling=True)
        except Exception as e:
            st.error(f"Could not load site: {e}")
    else:
        st.info("Enter a URL to start browsing.")

# Right Column: AI Assistant & Library
with col_assistant:
    st.subheader("🤖 Trae Assistant")
    
    # 1. Configuration (Mini)
    with st.expander("⚙️ Settings", expanded=False):
        use_mock = st.toggle("Mock Mode", value=os.getenv("USE_MOCK_DATA", "true").lower() == "true")
        content_type = st.selectbox("Type", ["tutorial", "concept"], label_visibility="collapsed")

    # 2. Analysis Logic
    if analyze_btn:
        with st.status("🧠 Trae is reading...", expanded=True) as status:
            try:
                clipper = VideoClipper()
                clipper.use_mock = use_mock
                refinery = ContentRefinery()
                refinery.use_mock = use_mock
                storage = StorageManager()

                st.write("Fetching content...")
                transcript = clipper.get_transcript(st.session_state.current_url)
                
                st.write("Analyzing...")
                markdown = refinery.refine_content(transcript, type=content_type)
                
                # Save immediately
                title_hint = "web_clip"
                if "douyin" in st.session_state.current_url: title_hint = "douyin_video"
                
                filepath = storage.save_markdown(markdown, title_hint)
                st.session_state.analysis_result = markdown
                st.session_state.last_saved_file = filepath
                
                status.update(label="Analysis Complete!", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Error: {e}")

    # 3. Result Display & Actions
    if st.session_state.analysis_result:
        st.success("✅ Content Ready")
        
        # Action Buttons
        ac_col1, ac_col2 = st.columns(2)
        with ac_col1:
            if st.button("💾 Save Context"):
                # Save to a fixed context file for easy referencing
                context_file = os.path.join("materials", "active_context.md")
                with open(context_file, "w", encoding="utf-8") as f:
                    f.write(st.session_state.analysis_result)
                st.toast("Saved to active_context.md!")
        
        with ac_col2:
            if st.button("🗑️ Clear"):
                st.session_state.analysis_result = None
                st.rerun()

        st.markdown("### 📝 Summary")
        st.markdown(st.session_state.analysis_result)
        
        if st.session_state.last_saved_file:
            st.caption(f"Source: `{os.path.basename(st.session_state.last_saved_file)}`")

    else:
        st.info("👋 Browse a website and click 'Analyze & Clip' to get started.")
        
    # 4. Quick Library Access
    st.divider()
    st.subheader("📚 Recent Clips")
    if os.path.exists("materials"):
        files = sorted([f for f in os.listdir("materials") if f.endswith(".md")], reverse=True)[:5]
        for f in files:
            if st.button(f"📄 {f}", key=f):
                with open(os.path.join("materials", f), "r", encoding="utf-8") as file:
                    st.session_state.analysis_result = file.read()
                    st.session_state.last_saved_file = os.path.join("materials", f)
                st.rerun()