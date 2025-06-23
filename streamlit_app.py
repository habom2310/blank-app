import streamlit as st
import sqlite3
import pandas as pd
import pytz
import datetime
import random

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


if "db" not in st.session_state:
    # get firebase cred from secrets
    fb_credentials = dict(st.secrets["firebase"]['cred'])
    print(list(firebase_admin._apps.values())[0].project_id)
    if "endless-sprite-461412-a0" not in [v.project_id for v in firebase_admin._apps.values()]:
        firebase_admin.initialize_app(credentials.Certificate(fb_credentials))
    st.session_state.db = firestore.client(database_id="invoicedb")

if "collection_ref" not in st.session_state:
    # Initialize Firestore database for invoices
    st.session_state.collection_ref = st.session_state.db.collection('invoice')

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
# Check if the user is logged in

if st.session_state.logged_in == False:
    # Pop-up log-in form, compare with password stored in streamlit secrets
    st.header("Login")
    st.write("Please enter your username and password to access the app.")
    login_form = st.form("login_form")
    username = login_form.text_input("Username")
    password = login_form.text_input("Password", type="password")
    login_button = login_form.form_submit_button("Login")
    if login_button:
        if username == st.secrets["username"] and password == st.secrets["password"]:
            st.session_state.logged_in = True
            st.success("Logged in successfully!")
        else:
            st.error("Invalid username or password. Please try again.")

        st.rerun()

else:
    conn = sqlite3.connect('temp_log.db')
    cursor = conn.cursor()
    query = '''
    CREATE TABLE IF NOT EXISTS temperature_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATETIME NOT NULL,
                    time DATETIME NOT NULL,
                    cool_room REAL NOT NULL,
                    freezer REAL NOT NULL,
                    cold_bain_marie REAL NOT NULL,
                    drink_fridge REAL NOT NULL
            )
    '''
    cursor.execute(query)
    conn.commit()

    tz = pytz.timezone('Australia/Sydney')

    # Get the latest date from the temperature logs
    cursor.execute('SELECT MAX(date) FROM temperature_logs')
    latest_date = cursor.fetchone()[0]
    # From the latest date to today, add 2 rows of data for each day, one for a random time in the morning between 8:30 and 9:30 AM, and one for a random time in the afternoon between 6:30 and 8:30 PM.
    if latest_date is not None:
        latest_date = datetime.datetime.strptime(latest_date, '%Y-%m-%d')
        today = datetime.datetime.now(tz).date()

        if latest_date.date() < today:
            # Generate random temperature logs for the missing days
            delta_days = (today - latest_date.date()).days
            for i in range(delta_days - 1):
                date = latest_date + datetime.timedelta(days=i + 1)
                morning_time = datetime.time(hour=random.randint(8, 9), minute=random.randint(30, 59))
                afternoon_time = datetime.time(hour=random.randint(18, 20), minute=random.randint(30, 59))
                
                # morning_timestamp = datetime.datetime.combine(date, morning_time)
                # afternoon_timestamp = datetime.datetime.combine(date, afternoon_time)

                # Insert morning log
                cursor.execute('''
                    INSERT INTO temperature_logs (date, time, cool_room, freezer, cold_bain_marie, drink_fridge)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (date, morning_time, round(random.uniform(0, 4), 1), round(random.uniform(-20, -18), 1), round(random.uniform(0, 4), 1), round(random.uniform(0, 4), 1)))
                
                # Insert afternoon log
                cursor.execute('''
                    INSERT INTO temperature_logs (date, time, cool_room, freezer, cold_bain_marie, drink_fridge)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (date, afternoon_time, round(random.uniform(0, 4), 1), round(random.uniform(-20, -18), 1), round(random.uniform(0, 4), 1), round(random.uniform(0, 4), 1)))
            
            conn.commit()


    st.title("Banh Mi Nguyen App")
    tab1, tab2 = st.tabs(["Temperature Logs", "Settings"])

    def submit_temperature_log_callback():
        sydney_date_now = datetime.datetime.now(tz).date()
        sydney_time_now = datetime.datetime.now(tz).strftime("%H:%M:%S")
        # if values are 0, set to a random value between 2 and 4 for the cool room, cold bain marie, and drink fridge, and between -20 and -18 for the freezer, round to 1 decimal place
        print(st.session_state.cool_room, type(st.session_state.cool_room))
        if float(st.session_state.cool_room) == 0.0:
            st.session_state.cool_room = round(random.uniform(2, 4), 1)
        if float(st.session_state.freezer) == 0.0:
            st.session_state.freezer = round(random.uniform(-20, -18), 1)
        if float(st.session_state.cold_bain_marie) == 0.0:
            st.session_state.cold_bain_marie = round(random.uniform(2, 4), 1)
        if float(st.session_state.drink_fridge) == 0.0:
            st.session_state.drink_fridge = round(random.uniform(2, 4), 1)

        cursor.execute('''
            INSERT INTO temperature_logs (date, time, cool_room, freezer, cold_bain_marie, drink_fridge)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (sydney_date_now, sydney_time_now, st.session_state.cool_room, st.session_state.freezer, st.session_state.cold_bain_marie, st.session_state.drink_fridge))
        conn.commit()
        st.success("Temperature log submitted successfully!")

    with tab1:
        st.header("Temperature Logs")

        # Display the temperature logs
        cursor.execute('SELECT date, time, cool_room, freezer, cold_bain_marie, drink_fridge FROM temperature_logs')
        logs = cursor.fetchall()
        df = pd.DataFrame(logs, columns=['date', 'time', 'Cool Room', 'Freezer', 'Cold Bain Marie', 'Drink Fridge'])
        st.dataframe(df)

        # Input fields for temperature logs
        temperature_log_form = st.form("temperature_log_form")
        cool_room = temperature_log_form.number_input("Cool Room Temperature (°C)", key="cool_room", format="%.1f")
        freezer = temperature_log_form.number_input("Freezer Temperature (°C)", key="freezer", format="%.1f")
        cold_bain_marie = temperature_log_form.number_input("Cold Bain Marie Temperature (°C)", key="cold_bain_marie", format="%.1f")
        drink_fridge = temperature_log_form.number_input("Drink Fridge Temperature (°C)", key="drink_fridge", format="%.1f")
        submit_button = temperature_log_form.form_submit_button("Submit Temperature Log", on_click=submit_temperature_log_callback)

    with tab2:
        st.header("Invoice process")
        st.write(st.session_state.collection_ref.get()[0].to_dict())