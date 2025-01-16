import streamlit as st

api_key = st.secrets["general"]["api_key"]
db_url = st.secrets["general"]["db_url"]

st.write(api_key)
st.write(db_url)