import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

DB_FILE = "savings_memory.db"

app = FastAPI()

# 🛑 CRITICAL: Allow your VS Code Chrome browser to access your phone
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows your computer to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goal_info (
            item TEXT,
            total INTEGER,
            current INTEGER,
            days INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# Data structures for receiving frontend data
class GoalSetup(BaseModel):
    item: str
    total: int
    current: int
    days: int

class DailyUpdate(BaseModel):
    amount_saved: int

init_db()

# --- ENDPOINT 1: Check if goal exists & send math data to frontend ---
@app.get("/api/goal")
def get_goal():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT item, total, current, days FROM goal_info LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return {"has_goal": False}
    
    buy, total_goal, current_save, days = row
    
    # Calculate Bro's Math Logic
    if days <= 0:
        daily_needed = 0
    else:
        daily_needed = round((total_goal - current_save) / days, 2)
        
    return {
        "has_goal": True,
        "item": buy,
        "total": total_goal,
        "current": current_save,
        "days_left": days,
        "daily_needed": daily_needed
    }

# --- ENDPOINT 2: Setup Goal (Replaces initial inputs) ---
@app.post("/api/setup")
def setup_goal(goal: GoalSetup):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM goal_info") # Clear any old goal
    cursor.execute("INSERT INTO goal_info VALUES (?, ?, ?, ?)", (goal.item, goal.total, goal.current, goal.days))
    conn.commit()
    conn.close()
    return {"status": "Goal setup successfully!"}

# --- ENDPOINT 3: Add Today's Savings (Replaces daily update logic) ---
@app.post("/api/update")
def update_progress(data: DailyUpdate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT total, current, days FROM goal_info LIMIT 1")
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return {"error": "No goal set yet"}
        
    total_goal, current_save, days = row
    
    # Save progress and subtract 1 day
    new_save = current_save + data.amount_saved
    new_days = max(0, days - 1) # Prevent days going below 0
    
    cursor.execute("UPDATE goal_info SET current = ?, days = ?", (new_save, new_days))
    conn.commit()
    conn.close()
    
    return {
        "status": "Saved!",
        "new_total_saved": new_save,
        "new_days_left": new_days
    }

if __name__ == "__main__":
    import os
    # Render provides the port automatically, default to 8000 if running locally
    port = int(os.environ.get("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)