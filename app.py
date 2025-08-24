import streamlit as st
import requests
import json
import re

# ==================== CONFIG ====================
API_KEY = "A51EcyRbnOg5j2WS0h-aOkeA7IoUzjzsGUmYQwYPFfL4"
DEPLOYMENT_ID = "67130972-4bf6-422f-b126-348ae0a5534c"
REGION = "us-south"
API_VERSION = "2021-05-01"
DEPLOYMENT_URL = f"https://{REGION}.ml.cloud.ibm.com/ml/v4/deployments/{DEPLOYMENT_ID}/ai_service?version={API_VERSION}"  # Use NON-streaming endpoint

# ==================== AUTH ====================
def get_token(api_key):
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"apikey": api_key, "grant_type": "urn:ibm:params:oauth:grant-type:apikey"}
    try:
        resp = requests.post(url, headers=headers, data=data)
        resp.raise_for_status()
        return resp.json().get("access_token")
    except requests.exceptions.RequestException as e:
        st.error(f"Authentication failed: {str(e)}")
        return None

# ==================== RESPONSE CLEANER ====================
def clean_response(response_text):
    """Remove the introductory line from the model's response"""
    # Remove lines that start with "Hi, I am Carenzaa" or similar introductions
    lines = response_text.split('\n')
    
    # Filter out introductory lines
    filtered_lines = []
    for line in lines:
        if not any(intro in line for intro in ["Hi, I am Carenzaa", "How can I help you", "I am Carenzaa"]):
            filtered_lines.append(line)
        elif "To become" in line or "Here's" in line:  # Keep lines that contain actual content
            filtered_lines.append(line)
    
    # Join the filtered lines back together
    cleaned_response = '\n'.join(filtered_lines).strip()
    
    # If we removed too much, return the original but without the first intro line
    if not cleaned_response or len(cleaned_response) < 20:
        # Remove just the first introductory line using regex
        cleaned_response = re.sub(r'^Hi, I am Carenzaa\..*?\.\s*', '', response_text)
        cleaned_response = re.sub(r'^Hi, I am Carenzaa\..*?\?\s*', '', cleaned_response)
    
    return cleaned_response if cleaned_response else response_text

# ==================== MODEL CALL ====================
def call_model(query):
    if not query or query.strip() == "":
        return {"error": "Empty query provided"}
    
    token = get_token(API_KEY)
    if not token:
        return {"error": "Authentication failed"}
    
    headers = {
        "Authorization": f"Bearer {token}", 
        "Content-Type": "application/json"
    }

    # Payload for the endpoint
    payload = {
        "messages": [
            {
                "content": query,
                "role": "user"
            }
        ]
    }

    try:
        resp = requests.post(DEPLOYMENT_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        
        # Parse the response
        response_data = resp.json()
        
        # Clean the response if it contains the intro text
        if "choices" in response_data and len(response_data["choices"]) > 0:
            original_content = response_data["choices"][0]["message"]["content"]
            cleaned_content = clean_response(original_content)
            response_data["choices"][0]["message"]["content"] = cleaned_content
        
        return response_data
            
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON response from API"}

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Agentic Career Counseling Companion", layout="wide")

# Title
st.markdown("""
    <h1 style='text-align:center;'>🎓 Agentic Career Counseling Companion</h1>
""", unsafe_allow_html=True)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "chat_input" not in st.session_state:
    st.session_state["chat_input"] = ""

# Layout: 3 columns
col1, col2, col3 = st.columns([1,2,2])

# ---------- Left column: Quick Career Questions ----------
with col1:
    st.subheader("💡 Quick Career Questions")
    
    quick_questions = {
        "What career is best for me based on my skills?": "What career is best for someone with skills in Python, machine learning, and problem-solving?",
        "How do I prepare for a career in AI/ML?": "How do I prepare for a career in AI/ML?",
        "Which jobs are in demand in 2025?": "Which jobs are in demand in 2025?",
        "Should I go for higher studies or a job?": "Should I go for higher studies or a job after computer science?"
    }
    
    for display_text, actual_query in quick_questions.items():
        if st.button(display_text, key=f"btn_{display_text[:10]}"):
            st.session_state["chat_input"] = actual_query
            st.rerun()

# ---------- Middle column: Career Chat Assistant ----------
with col2:
    st.subheader("💬 Career Chat Assistant")
    st.write("Ask me anything about your career:")

    chat_input = st.text_input(
        "Your question:", 
        value=st.session_state["chat_input"], 
        key="chatbox_input"
    )
    
    if st.button("Send", key="send_btn") and chat_input:
        with st.spinner("Analyzing your career question..."):
            response = call_model(chat_input)
            
            # Add to chat history
            st.session_state["chat_history"].append({
                "question": chat_input,
                "response": response
            })
            
            # Display response
            st.write("### Response:")
            
            if "error" in response:
                st.error(f"Error: {response['error']}")
            else:
                try:
                    if "choices" in response and len(response["choices"]) > 0:
                        message_content = response["choices"][0]["message"]["content"]
                        st.success(message_content)
                    else:
                        st.json(response)
                except Exception as e:
                    st.error(f"Error parsing response: {str(e)}")
                    st.json(response)

    # Display chat history
    if st.session_state["chat_history"]:
        st.subheader("Chat History")
        for i, chat in enumerate(st.session_state["chat_history"]):
            st.markdown(f"**Q:** {chat['question']}")
            if "error" in chat['response']:
                st.error(f"**A:** {chat['response']['error']}")
            else:
                try:
                    if "choices" in chat['response'] and len(chat['response']["choices"]) > 0:
                        message_content = chat['response']["choices"][0]["message"]["content"]
                        st.markdown(f"**A:** {message_content}")
                    else:
                        st.markdown(f"**A:** {str(chat['response'])[:200]}...")
                except Exception as e:
                    st.markdown(f"**A:** {str(chat['response'])[:200]}...")
            st.markdown("---")

# ---------- Right column: Career Insights & Recommendations ----------
with col3:
    st.subheader("📊 Career Insights & Recommendations")
    st.write("Click on a section below to explore career pathways:")

    career_pathways = {
        "🔹 AI & Data Science": [
            "Data Scientist", "Machine Learning Engineer", "AI Researcher",
            "Data Analyst", "Business Intelligence Analyst"
        ],
        "💻 Software Development": [
            "Full Stack Developer", "Mobile App Developer", "Cloud Engineer",
            "DevOps Engineer", "QA Automation Engineer"
        ],
        "📈 Business & Management": [
            "Business Analyst", "Product Manager", "Strategy Consultant",
            "Project Manager", "Operations Manager"
        ],
        "🎓 Research & Higher Studies": [
            "Pursue Masters/PhD in Emerging Tech", "Academic Researcher",
            "Think Tanks", "Research Scientist"
        ]
    }

    for category, careers in career_pathways.items():
        with st.expander(category):
            for career in careers:
                st.markdown(f"- {career}")

# Debug information
with st.expander("🔧 Debug Information"):
    st.write("**Using NON-streaming endpoint:** `/ai_service` instead of `/ai_service_stream`")
    st.write("**Response Format:** Complete JSON response (not SSE events)")
    st.write("**Endpoint:**", DEPLOYMENT_URL)

# Add some styling
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        margin-bottom: 5px;
    }
    .stExpander {
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)