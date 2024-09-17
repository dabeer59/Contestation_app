import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Initialize SQLite Database
def init_db():
    conn = sqlite3.connect('shift_manager.db')
    cursor = conn.cursor()

    # Create the time_adjustment_data table (formerly Late Coming)
    cursor.execute('''CREATE TABLE IF NOT EXISTS time_adjustment_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT,
        agent_name TEXT,
        date_of_adjustment TEXT,
        login_time TEXT,
        logout_time TEXT,
        login_status TEXT,
        extended_hours TEXT,
        leave_adjustment TEXT,
        remarks TEXT,
        approved_by_team_lead TEXT DEFAULT 'No',
        approved_by_manager TEXT DEFAULT 'No'
    )''')

    # Create the shift_swapping_data table
    cursor.execute('''CREATE TABLE IF NOT EXISTS shift_swapping_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT,
        osms TEXT,
        agent_name TEXT,
        shift TEXT,
        team_name TEXT,
        team_leader TEXT,
        site TEXT,
        swapped_with_osms TEXT,
        swapped_with_name TEXT,
        swapped_with_shift TEXT,
        approved_by_team_lead TEXT DEFAULT 'No',
        approved_by_manager TEXT DEFAULT 'No'
    )''')

    conn.commit()
    return conn

# Helper function to format time
def format_time(time_str):
    try:
        return datetime.strptime(time_str, '%H:%M').strftime('%I:%M %p')
    except ValueError:
        return time_str  # Return original if invalid

# Combined Approval Function for Team Lead and Manager with proper authentication steps
def approval_page(approval_type):
    st.title(f'{approval_type} Approval')

    # Persist authentication status in session
    if f'{approval_type}_authenticated' not in st.session_state:
        st.session_state[f'{approval_type}_authenticated'] = False

    # Check if authenticated
    if not st.session_state[f'{approval_type}_authenticated']:
        team_name = st.text_input(f'Enter {approval_type} Team Name')
        password = st.text_input(f'Enter {approval_type} Authentication Password', type='password')

        if st.button('Authenticate'):
            valid_password = (password == 'team_lead_pass') if approval_type == 'Team Lead' else (password == 'manager_pass')
            if valid_password:
                st.session_state[f'{approval_type}_authenticated'] = True
                st.session_state[f'{approval_type}_team_name'] = team_name
                st.success(f'{approval_type} authenticated successfully!')
            else:
                st.error('Invalid password or team name!')
                return

    else:
        st.info(f'{approval_type} authenticated!')

        team_name = st.session_state.get(f'{approval_type}_team_name')

        approval_section = st.selectbox('Select Section to Approve', ['Time Adjustment', 'Shift Swapping'])

        conn = init_db()
        cursor = conn.cursor()

        if approval_section == 'Time Adjustment':
            if approval_type == 'Team Lead':
                cursor.execute('SELECT * FROM time_adjustment_data WHERE approved_by_team_lead = "No"')
            else:
                cursor.execute('SELECT * FROM time_adjustment_data WHERE approved_by_team_lead = "Yes" AND approved_by_manager = "No"')
        else:
            if approval_type == 'Team Lead':
                cursor.execute('SELECT * FROM shift_swapping_data WHERE approved_by_team_lead = "No" AND team_name = ?', (team_name,))
            else:
                cursor.execute('SELECT * FROM shift_swapping_data WHERE approved_by_team_lead = "Yes" AND approved_by_manager = "No" AND team_name = ?', (team_name,))

        rows = cursor.fetchall()

        if rows:
            if approval_section == 'Time Adjustment':
                df = pd.DataFrame(rows, columns=[
                    'ID', 'Agent ID', 'Agent Name', 'Date of Adjustment', 'Login Time', 'Logout Time', 'Login Status', 'Extended Hours', 'Leave Adjustment', 'Remarks', 'Approved by Team Lead', 'Approved by Manager'
                ])
            else:
                df = pd.DataFrame(rows, columns=[
                    'ID', 'Entry Date', 'OSMS', 'Agent Name', 'Shift', 'Team Name', 'Team Leader', 'Site', 'Swapped with OSMS', 'Swapped with Name', 'Swapped with Shift', 'Approved by Team Lead', 'Approved by Manager'
                ])

            st.dataframe(df)

            selected_id = st.selectbox('Select Entry to Approve:', df['OSMS'])

            if st.button('Approve Entry'):
                if approval_type == 'Team Lead':
                    cursor.execute(f'UPDATE {"shift_swapping_data" if approval_section == "Shift Swapping" else "time_adjustment_data"} SET approved_by_team_lead = "Yes" WHERE osms = ?', (selected_id,))
                else:
                    cursor.execute(f'UPDATE {"shift_swapping_data" if approval_section == "Shift Swapping" else "time_adjustment_data"} SET approved_by_manager = "Yes" WHERE osms = ?', (selected_id,))

                conn.commit()
                st.success(f'Entry {selected_id} approved by {approval_type}!')
        else:
            st.write('No pending approvals for this section.')

# Display approved data
def approved_data_page():
    st.title('Approved Entries')

    approval_section = st.selectbox('Select Section to View', ['Time Adjustment', 'Shift Swapping'])

    team_name = st.text_input('Enter Team Name to Filter (Optional)')

    if st.button('Show Approved Data'):
        conn = init_db()
        cursor = conn.cursor()

        if approval_section == 'Time Adjustment':
            cursor.execute('SELECT * FROM time_adjustment_data WHERE approved_by_team_lead = "Yes" AND approved_by_manager = "Yes"')
        else:
            if team_name:
                cursor.execute('SELECT * FROM shift_swapping_data WHERE approved_by_team_lead = "Yes" AND approved_by_manager = "Yes" AND team_name = ?', (team_name,))
            else:
                cursor.execute('SELECT * FROM shift_swapping_data WHERE approved_by_team_lead = "Yes" AND approved_by_manager = "Yes"')

        rows = cursor.fetchall()

        if rows:
            if approval_section == 'Time Adjustment':
                df = pd.DataFrame(rows, columns=[
                    'ID', 'Agent ID', 'Agent Name', 'Date of Adjustment', 'Login Time', 'Logout Time', 'Login Status', 'Extended Hours', 'Leave Adjustment', 'Remarks', 'Approved by Team Lead', 'Approved by Manager'
                ])
            else:
                df = pd.DataFrame(rows, columns=[
                    'ID', 'Entry Date', 'OSMS', 'Agent Name', 'Shift', 'Team Name', 'Team Leader', 'Site', 'Swapped with OSMS', 'Swapped with Name', 'Swapped with Shift', 'Approved by Team Lead', 'Approved by Manager'
                ])

            st.dataframe(df)
        else:
            st.write('No approved data found for this section.')

# Data Entry Page with optional fields
def data_entry_page():
    st.title('Employee Shift Swapping & Time Adjustment')

    entry_type = st.selectbox('Select Entry Type', ['Time Adjustment', 'Shift Swapping'])

    if entry_type == 'Shift Swapping':
        entry_date = st.date_input('Select Date (Optional)', value=None)
        osms = st.text_input('OSMS (Optional)')
        agent_name = st.text_input('Agent Name (Required)')
        shift = st.text_input('Shift (Optional)')
        team_name = st.text_input('Team Name (Optional)')
        team_leader = st.text_input('Team Leader (Optional)')
        site = st.text_input('Site (Optional)')
        swapped_with_osms = st.text_input('Swapped With OSMS (Optional)')
        swapped_with_name = st.text_input('Swapped With Name (Optional)')
        swapped_with_shift = st.text_input('Swapped With Shift (Optional)')

        if st.button('Submit'):
            if agent_name:
                conn = init_db()
                cursor = conn.cursor()
                cursor.execute('''INSERT INTO shift_swapping_data (entry_date, osms, agent_name, shift, team_name, team_leader, site, swapped_with_osms, swapped_with_name, swapped_with_shift) 
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                               (entry_date, osms, agent_name, shift, team_name, team_leader, site, swapped_with_osms, swapped_with_name, swapped_with_shift))
                conn.commit()
                st.success('Shift Swapping Data Submitted Successfully!')
            else:
                st.error('Please fill in the required fields (Agent Name).')

    else:
        agent_id = st.text_input('Agent ID (Optional)')
        agent_name = st.text_input('Agent Name (Required)')
        date_of_adjustment = st.date_input('Date of Adjustment (Optional)', value=None)
        login_time = st.text_input('Login Time (Optional)')
        logout_time = st.text_input('Logout Time (Optional)')
        login_status = st.selectbox('Login Status (Optional)', ['On Time', 'Late', 'Absent'], index=0)
        extended_hours = st.text_input('Extended Hours (Optional)')
        leave_adjustment = st.text_input('Leave Adjustment (Optional)')
        remarks = st.text_area('Remarks (Optional)')

        if st.button('Submit'):
            if agent_name:
                conn = init_db()
                cursor = conn.cursor()
                cursor.execute('''INSERT INTO time_adjustment_data (agent_id, agent_name, date_of_adjustment, login_time, logout_time, login_status, extended_hours, leave_adjustment, remarks) 
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                               (agent_id, agent_name, date_of_adjustment, login_time, logout_time, login_status, extended_hours, leave_adjustment, remarks))
                conn.commit()
                st.success('Time Adjustment Data Submitted Successfully!')
            else:
                st.error('Please fill in the required fields (Agent Name).')

# Main function to navigate between pages
# def main():
#     st.sidebar.title('Navigation')
#     page = st.sidebar.radio('Go to:', ['Data Entry', 'Team Lead Approval', 'Manager Approval', 'Approved Data'])

#     if page == 'Data Entry':
#         data_entry_page()
#     elif page == 'Team Lead Approval':
#         approval_page('Team Lead')
#     elif page == 'Manager Approval':
#         approval_page('Manager')
#     elif page == 'Approved Data':
#         approved_data_page()

# if __name__ == '__main__':
#     main()
# Main function to navigate between pages
def main():
    
    # Add the company logo at the top of the sidebar
    logo_path = "logo.png"  # Ensure the logo file is in the same directory or specify the correct path
    st.sidebar.image(logo_path, use_column_width=True)

    page = st.sidebar.radio('Go to:', ['Data Entry', 'Team Lead Approval', 'Manager Approval', 'Approved Data'])

    if page == 'Data Entry':
        data_entry_page()
    elif page == 'Team Lead Approval':
        approval_page('Team Lead')
    elif page == 'Manager Approval':
        approval_page('Manager')
    elif page == 'Approved Data':
        approved_data_page()

if __name__ == '__main__':
    main()

