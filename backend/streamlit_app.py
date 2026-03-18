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

    tableData = []
    for result in st.session_state["results"]:
        quotes = " | ".join(result["relevantQuotes"])
        tableData.append({
            "Compliance Question": result["complianceQuestion"],
            "Compliance State": result["complianceState"],
            "Confidence": f"{result['confidence']}%",
            "Relevant Quotes": quotes,
            "Rationale": result["rationale"]
        })

    import pandas as pd
    df = pd.DataFrame(tableData)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Relevant Quotes": st.column_config.TextColumn(width="large"),
            "Rationale": st.column_config.TextColumn(width="large"),
        }
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
                reply = response.json()["reply"]

                st.session_state["chatHistory"].append({
                    "role": "assistant",
                    "content": reply
                })

                st.rerun()

            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")