try:
    import streamlit as st
    print("OK", st.__version__)
except Exception as e:
    print("ERROR", type(e).__name__, str(e))
