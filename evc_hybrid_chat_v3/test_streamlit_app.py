import streamlit as st

st.set_page_config(page_title="Test App")
st.title("Streamlit Test Page")
st.write("If you see this, Streamlit is rendering correctly.")
if st.button("Click me", help="A test button", key="test_btn"):
    st.write("Button clicked")
