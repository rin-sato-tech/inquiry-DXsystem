import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path

st.set_page_config(
    page_title="社内問い合わせ対応システム",
    layout="wide"
)

st.title("社内問い合わせ対応システム")
st.write("開発環境のセットアップが完了しています。")

st.info("次のステップで、CSV取り込みとSQLite管理を実装します。")