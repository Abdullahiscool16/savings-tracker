import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

DB_FILE = "savings_v2.db"

app = FastAPI()

# Allow connections from any frontend over the cloud
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 🎯 FIX: Added username as PRIMARY KEY to isolate accounts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goal_info (
            username TEXT PRIMARY KEY,
            item TEXT,
            total INTEGER,
            current INTEGER,
            days INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# Data structures matching your updated frontend variables + username
class GoalSetup(BaseModel):
    username: str  # 🎯 New field
    item: str
    total: int
    current: int
    days: int

class DailyUpdate(BaseModel):
    username: str  # 🎯 New field
    amount: int  

init_db()

# --- ENDPOINT 1: Get goal for a SPECIFIC user ---
# Note the path parameter: /api/goal/abdullah
@app.get("/api/goal/{username}")
def get_goal(username: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT item, total, current, days FROM goal_info WHERE username = ?", (username.lower(),))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return {"has_goal": False}
    
    buy, total_goal, current_save, days = row
    
    if days <= 0:
        daily_needed = 0
    else:
        # 🎯 FIX: Changed to round to the nearest whole rupee (no decimal tail)
        daily_needed = round((total_goal - current_save) / days)
        
    return {
        "has_goal": True,
        "item": buy,
        "total": total_goal,
        "current": current_save,
        "days": days,  
        "daily_needed": daily_needed
    }

# --- ENDPOINT 2: Setup Goal for a SPECIFIC user ---
@app.post("/api/setup")
def setup_goal(goal: GoalSetup):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 🎯 FIX: Insert new user or overwrite only their specific goal row if they exist
    cursor.execute('''
        INSERT INTO goal_info (username, item, total, current, days) 
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            item=excluded.item,
            total=excluded.total,
            current=excluded.current,
            days=excluded.days
    ''', (goal.username.lower(), goal.item, goal.total, goal.current, goal.days))
    conn.commit()
    conn.close()
    return {"status": "Goal setup successfully!"}

# --- ENDPOINT 3: Add Today's Savings for a SPECIFIC user ---
@app.post("/api/update")
def update_progress(data: DailyUpdate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 🎯 FIX: Fetch details only for this user
    cursor.execute("SELECT item, total, current, days FROM goal_info WHERE username = ?", (data.username.lower(),))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return {"error": "No goal set yet"}
        
    buy, total_goal, current_save, days = row
    
    new_save = current_save + data.amount
    new_days = max(0, days - 1) 
    
    # 🎯 FIX: Update only this user's specific row
    cursor.execute("UPDATE goal_info SET current = ?, days = ? WHERE username = ?", (new_save, new_days, data.username.lower()))
    conn.commit()
    conn.close()
    
    return {
        "has_goal": True,
        "item": buy,
        "total": total_goal,
        "current": new_save,
        "days": new_days
    }

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080)) 
    uvicorn.run(app, host="0.0.0.0", port=port)
