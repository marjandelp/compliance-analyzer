import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("Contract Compliance Analyzer")
st.write("Upload a PDF contract to check compliance against security requirements.")

uploadedFile = st.file_uploader("Choose a PDF file", type="pdf")

if uploadedFile is not None:
    if st.button("Analyze Contract"):
        with st.spinner("Parsing and analyzing contract, this may take a moment..."):
            try:
                fileBytes = uploadedFile.read()
                
                response = requests.post(
                    f"{API_URL}/analyze",
                    files={"file": (uploadedFile.name, fileBytes, "application/pdf")}
                )
                
                if response.status_code != 200:
                    st.error(f"Backend error: {response.text}")
                else:
                    data = response.json()
                    st.session_state["results"] = data["results"]
                    st.session_state["sessionId"] = data["sessionId"]
                    st.session_state["chatHistory"] = []

            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")

if "results" in st.session_state:
    st.subheader("Compliance Results")

    import pandas as pd

    tableData = []
    for result in st.session_state["results"]:
        quotes = "\n\n".join(result["relevantQuotes"]) if result["relevantQuotes"] else "None found"
        tableData.append({
            "Compliance Question": result["complianceQuestion"],
            "Compliance State": result["complianceState"],
            "Confidence": f"{result['confidence']}%",
            "Relevant Quotes": quotes,
            "Rationale": result["rationale"]
        })

    df = pd.DataFrame(tableData)

    col_widths = {
        "Compliance Question": "14%",
        "Compliance State": "10%",
        "Confidence": "8%",
        "Relevant Quotes": "38%",
        "Rationale": "30%"
    }

    html = "<table style='width:100%; table-layout:fixed; border-collapse:collapse; font-size:13px;'>"
    
    # Header
    html += "<tr>"
    for col in df.columns:
        html += f"<th style='text-align:left; padding:8px; background-color:#0F2B46; color:white; width:{col_widths[col]};'>{col}</th>"
    html += "</tr>"
    
    # Rows
    for _, row in df.iterrows():
        html += "<tr style='border-bottom:1px solid #E2E8F0;'>"
        for col in df.columns:
            val = str(row[col]).replace('\n', '<br>')
            html += f"<td style='padding:8px; vertical-align:top; white-space:pre-wrap; word-wrap:break-word;'>{val}</td>"
        html += "</tr>"
    
    html += "</table>"

    st.markdown(
        f"<div style='overflow-x:auto; overflow-y:auto; max-height:500px;'>{html}</div>",
        unsafe_allow_html=True
    )

if "sessionId" in st.session_state:
    st.subheader("Chat with your Contract")
    st.write("Ask any question about the contract.")

    for msg in st.session_state.get("chatHistory", []):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    userInput = st.chat_input("Ask a question about the contract...")

    if userInput:
        st.session_state["chatHistory"].append({
            "role": "user",
            "content": userInput
        })

        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "sessionId": st.session_state["sessionId"],
                        "message": userInput,
                        "history": st.session_state["chatHistory"]
                    }
                )
                data = response.json()
                if "reply" in data:
                    reply = data["reply"]
                else:
                    st.error(f"Chat error: {data}")
                    st.stop()

                st.session_state["chatHistory"].append({
                    "role": "assistant",
                    "content": reply
                })

                st.rerun()

            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")