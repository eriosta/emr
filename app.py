import altair as alt
import streamlit as st
import pandas as pd
import numpy as np
import jotform
import toml

# Load the configuration file
config = toml.load("config.toml")

# Access the API key
api_key = st.secrets["credentials"]["api_key"]
form_id = st.secrets["credentials"]["form_id"]

client = jotform.JotformAPIClient(api_key)

# Number of submissions to exclude
exclude_count = 25

# Retrieve form details to get the order of questions
form_details = client.get_form(form_id)

# Retrieve all submissions using pagination
all_submissions = []
offset = 0
limit = 1000  # You can adjust this based on the API limit

while True:
    submissions = client.get_form_submissions(form_id, offset=offset, limit=limit)
    if not submissions:
        break
    all_submissions.extend(submissions)
    offset += limit

# Remove the last 25 submissions from the last page
if len(all_submissions) > exclude_count:
    all_submissions = all_submissions[:-exclude_count]

# Extract data
data = []
questions = {}

for submission in all_submissions:
    fields = {}
    for key, value in submission['answers'].items():
        if 'answer' in value:
            question = value['text']
            answer = value['answer']
            fields[question] = answer
            questions[question] = True
    data.append(fields)

# Create DataFrame ensuring all columns are included
all_questions = list(questions.keys())
df = pd.DataFrame(data, columns=all_questions)

df.to_csv('submissions.csv',index=False)

# Eligibility
# 1. Completed survey
SSs1 = 'Please answer the following question to continue with the survey. Are you employed by a healthcare provider organization in the Asia-Pacific region?'
PACafv289 = '"The additional features available for purchase in our EMR provide good value."'
df = df[df[SSs1].notna() & df[PACafv289].notna()]

# 2. One response per email and email cannot be free
CIe2 = 'Please enter your work email'
df = df.drop_duplicates(subset=CIe2)
mask = df[CIe2].str.endswith('@gmail.com')
df = df[~mask]

# 3. No nonsense
# Drop rows that have a string that starts with "the best" (use lowercase)
for column in df.columns:
    try:
        df = df[~df[column].str.lower().str.startswith('the best', na=False)]
    except AttributeError:
        continue

df.loc[df['In what country do you use your EMR? Select your primary location.'].isna(), 'In what country do you use your EMR? Select your primary location.'] = 'Thailand'

required_columns = [
    'In what country do you use your EMR? Select your primary location.',
    'What type of healthcare and/or IT user best describes your role?'
]

df = df[required_columns]


# Group and count data for the chart
country_counts = df['In what country do you use your EMR? Select your primary location.'].value_counts().reset_index()
country_counts.columns = ['Country', 'Count']

# Create bar chart for country_df
country_chart = alt.Chart(country_counts).mark_bar().encode(
    x=alt.X('Count:Q', title='Count'),
    y=alt.Y('Country:N', title='Country', sort='-x'),
    color=alt.Color('Country:N', legend=None)
).properties(
    width=550,
    height=1000,
    title='Count of Users by Country'
)

# Create bar chart for role_df
role_chart = alt.Chart(df).mark_bar().encode(
    x='count()',
    y=alt.Y('What type of healthcare and/or IT user best describes your role?', title='Role', sort='-x'),
    color=alt.Color('What type of healthcare and/or IT user best describes your role?', legend=None)
).properties(
    width=550,
    height=300,
    title='Count of Users by Role'
)

# Display the charts in Streamlit
total_responses = len(df)
st.metric(label="Total Number of Responses", value=total_responses)

st.altair_chart(country_chart)
st.altair_chart(role_chart)

