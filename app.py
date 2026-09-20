import streamlit as st
import psycopg2
from PyPDF2 import PdfReader
from google import genai

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def db():
    return psycopg2.connect(st.secrets["DATABASE_URL"])


st.title("AI Notes Generator")

menu = st.sidebar.selectbox("Menu", ["Login", "Register"])


if menu == "Register":
    u = st.text_input("Username", key="reg_user")
    p = st.text_input("Password", type="password", key="reg_pass")

    if st.button("Register"):
        d = db()
        c = d.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50),
                password VARCHAR(50)
            )
            """
        )

        c.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (u, p)
        )

        d.commit()
        c.close()
        d.close()

        st.success("Registered")


if menu == "Login":
    u = st.text_input("Username", key="login_user")
    p = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login"):
        d = db()
        c = d.cursor()

        c.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (u, p)
        )

        if c.fetchone():
            st.session_state["u"] = u
            st.success("Logged in")
        else:
            st.error("Invalid")

        c.close()
        d.close()


if "u" in st.session_state:
    f = st.file_uploader("PDF", type=["pdf"])

    if f:
        r = PdfReader(f)
        t = ""

        for p in r.pages:
            text = p.extract_text()

            if text:
                t += text

        if st.button("Generate"):
            res = client.models.generate_content(
                model="gemini-3.6-flash",
                contents="Make short notes:\n" + t[:3000]
            )

            out = res.text
            st.write(out)