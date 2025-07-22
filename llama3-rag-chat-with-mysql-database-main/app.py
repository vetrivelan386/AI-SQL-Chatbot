import streamlit as st
import urllib.parse
from langchain_community.chat_models import ChatOllama
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate

# Connect to MySQL database
def connectDatabase(username, port, host, password, database):
    encoded_password = urllib.parse.quote_plus(password)
    mysql_uri = f"mysql+mysqlconnector://{username}:{encoded_password}@{host}:{port}/{database}"
    st.session_state.db = SQLDatabase.from_uri(mysql_uri)

# Run SQL query
def runQuery(query):
    return st.session_state.db.run(query) if st.session_state.db else "Please connect to database"

# Get schema of the connected database
def getDatabaseSchema():
    return st.session_state.db.get_table_info() if st.session_state.db else "Please connect to database"

# Clean LLM-generated SQL query (removes markdown ```sql blocks)
def clean_query_output(query):
    return query.strip().replace("```sql", "").replace("```", "").strip()

# Initialize LLM
llm = ChatOllama(model="gemma:2b")

# Generate SQL query from user's question using LLM
def getQueryFromLLM(question):
    template = """below is the schema of MYSQL database, read the schema carefully about the table and column names. Also take care of table or column name case sensitivity.
    Finally answer user's question in the form of SQL query.

    {schema}

    please only provide the SQL query and nothing else

    for example:
    question: how many albums we have in database
    SQL query: SELECT COUNT(*) FROM album
    question: how many customers are from Brazil in the database ?
    SQL query: SELECT COUNT(*) FROM customer WHERE country=Brazil

    your turn :
    question: {question}
    SQL query :
    please only provide the SQL query and nothing else
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm

    response = chain.invoke({
        "question": question,
        "schema": getDatabaseSchema()
    })
    return response.content

# Generate natural language response from SQL result
def getResponseForQueryResult(question, query, result):
    template2 = """below is the schema of MYSQL database, read the schema carefully about the table and column names of each table.
    Also look into the conversation if available
    Finally write a response in natural language by looking into the conversation and result.

    {schema}

    Here are some example for you:
    question: how many albums we have in database
    SQL query: SELECT COUNT(*) FROM album;
    Result : [(34,)]
    Response: There are 34 albums in the database.

    question: how many users we have in database
    SQL query: SELECT COUNT(*) FROM customer;
    Result : [(59,)]
    Response: There are 59 amazing users in the database.

    question: how many users above are from india we have in database
    SQL query: SELECT COUNT(*) FROM customer WHERE country=india;
    Result : [(4,)]
    Response: There are 4 amazing users in the database.

    your turn to write response in natural language from the given result :
    question: {question}
    SQL query : {query}
    Result : {result}
    Response:
    """

    prompt2 = ChatPromptTemplate.from_template(template2)
    chain2 = prompt2 | llm

    response = chain2.invoke({
        "question": question,
        "schema": getDatabaseSchema(),
        "query": query,
        "result": result
    })

    return response.content

# Streamlit app configuration
st.set_page_config(
    page_icon="🤖",
    page_title="Chat with MYSQL DB",
    layout="centered"
)

question = st.chat_input('Chat with your mysql database')

if "chat" not in st.session_state:
    st.session_state.chat = []

if question:
    if "db" not in st.session_state:
        st.error('Please connect database first.')
    else:
        st.session_state.chat.append({
            "role": "user",
            "content": question
        })

        query = getQueryFromLLM(question)
        cleaned_query = clean_query_output(query)
        print("Generated Query:", cleaned_query)
        result = runQuery(cleaned_query)
        print("Query Result:", result)
        response = getResponseForQueryResult(question, cleaned_query, result)

        st.session_state.chat.append({
            "role": "assistant",
            "content": response
        })

# Display chat history
for chat in st.session_state.chat:
    st.chat_message(chat['role']).markdown(chat['content'])

# Sidebar for DB connection
with st.sidebar:
    st.title('Connect to database')
    st.text_input(label="Host", key="host", value="localhost")
    st.text_input(label="Port", key="port", value="3306")
    st.text_input(label="Username", key="username", value="root")
    st.text_input(label="Password", key="password", value="", type="password")
    st.text_input(label="Database", key="database", value="rag_test")
    connectBtn = st.button("Connect")

if connectBtn:
    connectDatabase(
        username=st.session_state.username,
        port=st.session_state.port,
        host=st.session_state.host,
        password=st.session_state.password,
        database=st.session_state.database,
    )
    st.success("Database connected ✅")
