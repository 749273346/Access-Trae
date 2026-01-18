import streamlit as st
import os
import sys
from dotenv import load_dotenv

# Add current directory to path to import src modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.clipper import VideoClipper
from src.refinery import ContentRefinery
from src.storage import StorageManager

# Load env variables
load_dotenv()

st.set_page_config(
    page_title="Trae Omni-Browser Clipper",
    page_icon="🎬",
    layout="wide"
)

st.title("Trae Omni-Browser Clipper 🚀")
st.markdown("Extract insights and code from videos directly into your IDE.")

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    
    use_mock = st.toggle("Use Mock Data", value=os.getenv("USE_MOCK_DATA", "true").lower() == "true")
    if not use_mock:
        supadata_key = st.text_input("Supadata API Key", type="password", value=os.getenv("SUPADATA_API_KEY", ""))
        openai_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        
        # Update env vars in runtime (simple hack for session)
        if supadata_key: os.environ["SUPADATA_API_KEY"] = supadata_key
        if openai_key: os.environ["OPENAI_API_KEY"] = openai_key
    else:
        st.info("Running in Mock Mode. No API keys required.")

    st.divider()
    st.write("Output Directory:")
    st.code(os.path.abspath("materials"))

# Main Interface
col1, col2 = st.columns([2, 1])

with col1:
    url = st.text_input("Video URL", placeholder="Paste YouTube, TikTok, or Bilibili link here...")
    
    content_type = st.selectbox(
        "Content Type",
        ["tutorial", "concept"],
        format_func=lambda x: "Code Tutorial 👨‍💻" if x == "tutorial" else "Concept Explanation 🧠"
    )

    if st.button("Analyze & Clip", type="primary", use_container_width=True):
        if not url:
            st.warning("Please enter a URL first.")
        else:
            try:
                # Initialize Modules
                clipper = VideoClipper()
                # Force mock update based on UI toggle
                clipper.use_mock = use_mock
                
                refinery = ContentRefinery()
                refinery.use_mock = use_mock
                
                storage = StorageManager()

                with st.status("Processing...", expanded=True) as status:
                    st.write("📥 Fetching transcript from video...")
                    transcript = clipper.get_transcript(url)
                    st.write("✅ Transcript acquired.")
                    
                    st.write("🧠 Analyzing content with AI...")
                    markdown_content = refinery.refine_content(transcript, type=content_type)
                    st.write("✅ Content refined.")
                    
                    st.write("💾 Saving to local library...")
                    # Generate a simple title hint from URL or content
                    title_hint = "video_note"
                    if "python" in url.lower(): title_hint = "python_tutorial"
                    
                    file_path = storage.save_markdown(markdown_content, title_hint)
                    st.write(f"✅ Saved to: {file_path}")
                    
                    status.update(label="Process Complete!", state="complete", expanded=False)

                st.success("Done! Preview below:")
                st.markdown("---")
                st.markdown(markdown_content)

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

with col2:
    st.header("Recent Clips")
    # Simple file explorer for materials folder
    materials_dir = "materials"
    if os.path.exists(materials_dir):
        files = sorted(os.listdir(materials_dir), reverse=True)
        for f in files:
            if f.endswith(".md"):
                if st.button(f"📄 {f}", key=f):
                    with open(os.path.join(materials_dir, f), "r", encoding="utf-8") as file:
                        st.session_state['preview_file'] = file.read()
                        st.session_state['preview_filename'] = f

    if 'preview_file' in st.session_state:
        with st.expander(f"Preview: {st.session_state.get('preview_filename')}", expanded=True):
            st.text_area("Content", st.session_state['preview_file'], height=300)
