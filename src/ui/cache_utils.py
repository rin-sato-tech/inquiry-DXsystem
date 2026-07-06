import streamlit as st


def clear_cache() -> None:
    """Streamlitのキャッシュをクリアし、DB更新後の再読み込みを反映する。"""
    st.cache_data.clear()