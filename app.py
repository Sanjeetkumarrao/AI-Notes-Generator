import streamlit as st
import os
import psycopg2
import bcrypt

from PyPDF2 import PdfReader
from google import genai


client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)



def db():
    return psycopg2.connect(
        os.getenv("DATABASE_URL")
    )



st.title("AI Notes Generator")


menu = st.sidebar.selectbox(
    "Menu",
    ["Login", "Register"]
)



if menu == "Register":

    u = st.text_input(
        "Username",
        key="reg_user"
    )

    p = st.text_input(
        "Password",
        type="password",
        key="reg_pass"
    )

    if st.button("Register"):

        if not u or not p:
            st.error("Username and password are required.")

        elif len(p.encode("utf-8")) > 72:
            st.error("Password must be 72 bytes or less.")

        else:

            d = db()
            c = d.cursor()

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username VARCHAR(50) PRIMARY KEY,
                    password VARCHAR(255) NOT NULL
                )
                """
            )

            c.execute(
                "SELECT username FROM users WHERE username = %s",
                (u,)
            )

            existing_user = c.fetchone()

            if existing_user:

                st.error("Username already exists.")

            else:

                hashed_password = bcrypt.hashpw(
                    p.encode("utf-8"),
                    bcrypt.gensalt()
                ).decode("utf-8")

                c.execute(
                    """
                    INSERT INTO users (username, password)
                    VALUES (%s, %s)
                    """,
                    (u, hashed_password)
                )

                d.commit()

                st.success("Registered successfully.")

            c.close()
            d.close()



if menu == "Login":

    u = st.text_input(
        "Username",
        key="login_user"
    )

    p = st.text_input(
        "Password",
        type="password",
        key="login_pass"
    )

    if st.button("Login"):

        d = db()
        c = d.cursor()

        c.execute(
            """
            SELECT password
            FROM users
            WHERE username = %s
            """,
            (u,)
        )

        user = c.fetchone()

        if user:

            stored_password = user[0]

            try:

                password_correct = bcrypt.checkpw(
                    p.encode("utf-8"),
                    stored_password.encode("utf-8")
                )

            except ValueError:

                password_correct = False

            if password_correct:

                st.session_state["u"] = u
                st.success("Logged in successfully.")

            else:

                st.error("Invalid username or password.")

        else:

            st.error("Invalid username or password.")

        c.close()
        d.close()



if "u" in st.session_state:

    st.write(f"Welcome, {st.session_state['u']}")

    f = st.file_uploader(
        "PDF",
        type=["pdf"]
    )

    if f:

        r = PdfReader(f)

        t = ""

        for page in r.pages:

            text = page.extract_text()

            if text:
                t += text

        if st.button("Generate"):

            d = db()
            c = d.cursor()


            c.execute(
                """
                CREATE TABLE IF NOT EXISTS api_usage (
                    username VARCHAR(50) PRIMARY KEY,
                    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    count INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            c.execute(
                """
                SELECT usage_date, count
                FROM api_usage
                WHERE username = %s
                FOR UPDATE
                """,
                (st.session_state["u"],)
            )

            usage = c.fetchone()

            allowed = False


            if usage is None:

                c.execute(
                    """
                    INSERT INTO api_usage
                    (username, count)
                    VALUES (%s, 1)
                    """,
                    (st.session_state["u"],)
                )

                d.commit()

                allowed = True

            else:

                usage_date, count = usage


                if usage_date < __import__("datetime").date.today():

                    c.execute(
                        """
                        UPDATE api_usage
                        SET usage_date = CURRENT_DATE,
                            count = 1
                        WHERE username = %s
                        """,
                        (st.session_state["u"],)
                    )

                    d.commit()

                    allowed = True

                elif count >= 5:

                    d.rollback()

                    allowed = False

                else:

                    c.execute(
                        """
                        UPDATE api_usage
                        SET count = count + 1
                        WHERE username = %s
                        """,
                        (st.session_state["u"],)
                    )

                    d.commit()

                    allowed = True

            c.close()
            d.close()


            if allowed:

                try:

                    res = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=(
                            "Make short notes from this PDF:\n\n"
                            + t[:3000]
                        )
                    )

                    st.write(res.text)

                except Exception as e:

                    st.error(
                        "Something went wrong while generating notes."
                    )

                    st.error(str(e))

            else:

                st.warning(
                    "Daily limit reached. "
                    "You can generate 5 notes per day."
                )