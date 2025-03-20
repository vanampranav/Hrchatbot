from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import sqlite3
import uuid
import openai

app = FastAPI()

# ✅ Set OpenAI API Key directly in the code (⚠️ Not recommended for production)
OPENAI_API_KEY = "your-openai-api-key-here"

# ✅ Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ✅ Database setup
def get_db_connection():
    conn = sqlite3.connect("grievances.db")
    conn.execute("PRAGMA foreign_keys = ON;")  # Ensure foreign key constraints are enabled
    return conn

def create_table():
    """Creates the grievances table if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS grievances (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            message TEXT,
            anonymous BOOLEAN
        )"""
    )
    conn.commit()
    conn.close()

create_table()  # Ensure table is created on startup

# ✅ Define Grievance model
class Grievance(BaseModel):
    name: str = None
    email: str = None
    message: str
    anonymous: bool

# ✅ Predefined FAQs
faqs = {
    "leave policy": "Employees are entitled to 20 paid leaves per year.",
    "work from home": "Employees can work from home up to 2 days per week.",
    "health benefits": "We provide health insurance covering up to $5000 per year.",
    "probation period": "The probation period for new employees is 6 months.",
    "overtime policy": "Employees are compensated for overtime at 1.5 times the regular hourly rate.",
    "dress code": "Employees are expected to wear business casual attire.",
    "salary increment": "Salary increments are performance-based and reviewed annually.",
    "training programs": "The company offers regular training sessions on skill development.",
    "travel reimbursement": "Employees can claim travel expenses for official work trips.",
    "retirement benefits": "Employees are eligible for a pension plan after 5 years of service."
}

# ✅ Submit a grievance
@app.post("/submit_grievance/", summary="Submit a grievance")
def submit_grievance(grievance: Grievance):
    grievance_id = str(uuid.uuid4())[:8]  # Generate a short unique ID
    name = None if grievance.anonymous else grievance.name
    email = None if grievance.anonymous else grievance.email

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO grievances (id, name, email, message, anonymous) VALUES (?, ?, ?, ?, ?)",
        (grievance_id, name, email, grievance.message, grievance.anonymous),
    )
    conn.commit()
    conn.close()

    return {"ticket_id": grievance_id, "message": "Grievance submitted successfully."}

# ✅ Get all grievances
@app.get("/get_grievances/", summary="Fetch all grievances")
def get_grievances():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, email, message, anonymous FROM grievances")
    grievances = [
        {
            "ticket_id": row[0],
            "name": row[1] if row[1] is not None else "Anonymous",
            "email": row[2] if row[2] is not None else "Hidden",
            "message": row[3],
        }
        for row in cursor.fetchall()
    ]
    
    conn.close()
    return {"grievances": grievances}

# ✅ Fetch FAQ or AI-generated response
@app.get("/faq", summary="Fetch FAQ response")
def get_faq(question: str = Query(..., description="Enter your question")):
    """
    - If the question matches predefined FAQs → return the response.
    - Otherwise → send the query to OpenAI's GPT-4 Turbo.
    """
    
    # 🔹 Check for FAQ match first
    for key, answer in faqs.items():
        if key in question.lower():
            return {"response": answer}

    # 🔹 If not found, ask OpenAI
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an HR assistant. Answer questions clearly and concisely."},
                {"role": "user", "content": question}
            ],
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        return {"response": ai_response}
    
    except openai.AuthenticationError:
        return {"response": "⚠️ Invalid OpenAI API Key. Please check your key and try again."}
    
    except openai.OpenAIError as e:
        return {"response": f"⚠️ OpenAI Error: {str(e)}"}

