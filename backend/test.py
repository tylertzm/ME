import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# --- MongoDB Setup ---
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client["thought_db"]
thoughts_col = db["thoughts"]

# --- Helper Functions ---
def add_thought(text):
    thoughts_col.insert_one({"text": text, "timestamp": datetime.now()})

def update_thought(_id, new_text):
    thoughts_col.update_one({"_id": _id}, {"$set": {"text": new_text}})

def search_thoughts(query):
    return list(thoughts_col.find({"text": {"$regex": query, "$options": "i"}}))

def get_daily_summary():
    today = datetime.now().date()
    return list(thoughts_col.find({"timestamp": {"$gte": datetime(today.year, today.month, today.day)}}))

def main():
    st.title("Thought Tracker App")

    menu = st.sidebar.selectbox("Choose Action", ["Submit Thought", "Knowledge Search", "Daily Summary"])

    if menu == "Submit Thought":
        st.header("Restack Agent 1: Submit Thought")
        thought = st.text_area("What's on your mind?")
        if st.button("Submit"):
            add_thought(thought)
            st.success("Thought submitted!")

    elif menu == "Knowledge Search":
        st.header("Restack Agent 2: Knowledge Search")
        query = st.text_input("Search your thoughts")
        if st.button("Search"):
            results = search_thoughts(query)
            for r in results:
                st.write(f"- {r['text']} ({r['timestamp']})")

    elif menu == "Daily Summary":
        st.header("Restack Agent 3: Daily Summary")
        summary = get_daily_summary()
        st.write("Today's Thoughts:")
        for s in summary:
            st.write(f"- {s['text']} ({s['timestamp']})")


if __name__ == "__main__":
    main()
       
