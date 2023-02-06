import json
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import jwt
from passlib.context import CryptContext
import pymysql
import wheel
import cryptography
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)
"""ONLY LOCALHOST"""
DATABASE_URL = pymysql.connect(host='127.0.0.1', user='root', password='root', db='todo_list')

app = FastAPI()


class DBConnection:
    def __init__(self,url):
        self.conn = DATABASE_URL

    def get_conn(self):
        """
        Returns a database connection instance.
        """
        return self.conn

    def close(self):
        """
        Closes the database connection.
        """
        self.conn.close()
"""ALL MODELS USED"""
class Token(BaseModel):
    access_token: str
    token_type: str
class Task(BaseModel):
    title: str
    description: str
    status: str

class UserModel(BaseModel):
    username: str
    password: str
    email: str

class User:
    def __init__(self, conn):
        self.conn = conn

    async def create(self, username: str, password: str, email: str):
        """CREATES THE USER"""
        cursor = self.conn.cursor()
        sql = "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)"
        cursor.execute(sql, (username, password, email))
        self.conn.commit()
        return cursor.lastrowid

    async def get(self, user_id: int):
        """RETRIVES THE USER BASED ON ID"""
        cursor = self.conn.cursor()
        sql = "SELECT id, username, email FROM users WHERE id=%s"
        cursor.execute(sql, (user_id,))
        return cursor.fetchone()

    async def authenticate(self, username: str, password: str):
        """USER AUTHENTICATION FOR REGISTRATION AND LOGIN"""
        cursor = self.conn.cursor()
        sql = "SELECT id, username, password, email FROM users WHERE username=%s"
        cursor.execute(sql, (username,))
        user1 = cursor.fetchone()
        user = self.get(user1[0])
        if user and pwd_context.verify(password, user1[2]):
            return user1
        else:
            return None


class Auth:
    def __init__(self):
        pass

    def create_access_token(data: dict):
        """
        Creates an access token for the given data.
        """
        encoded_jwt = jwt.encode(data, secret_key, algorithm="HS256")
        print(encoded_jwt)
        return encoded_jwt
"""ALL ENDPOINTS """
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

db = DBConnection(DATABASE_URL)
conn = db.get_conn()

user = User(conn)
secret_key = "KjyK23MNM9p7bexxE33LcFbYk6Zdg7r2"
auth = Auth()
global_user_id = None
def get_password_hash(password: str):
    """MAKES HASED PASSWORD FOR USERS AFTER REGISTRATION"""
    return pwd_context.hash(password)
@app.get("/")
def root():
    """ROOT ENDPOINT"""
    return {"To Do List API, checkout /register first , /token for login, /tasks for tasks /tasks/task_id to update or delete tasks"}

@app.post("/register")
async def register(userModel: UserModel):
    """REGISTRATION ENDPOINT"""
    user = User(conn)
    hashed_password = get_password_hash(userModel.password)
    user_id = await user.create(username=userModel.username, password=hashed_password, email=userModel.email)
    return {"message": "User created successfully.", "user_id": user_id}


@app.post("/login")
async def login(data: OAuth2PasswordRequestForm = Depends()):
    """LOGIN ENDPOINT"""
    global global_user_id
    user = await User(conn).authenticate(data.username, data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = Auth.create_access_token(data={"sub": user[1]})
    global_user_id = user[0]
    return {"access_token": access_token, "token_type": "bearer"}


class TaskMethods:
    @staticmethod
    async def create_task(task_data:Task):
        """CREATES TASKS IN THE DATABASE """
        global global_user_id
        cursor = DATABASE_URL.cursor()
        query = "INSERT INTO tasks (title, description,status, user_id) VALUES (%s, %s,%s, %s)"
        cursor.execute(query, (task_data.title, task_data.description,task_data.status, global_user_id))
        conn.commit()
        query = "SELECT * FROM tasks ORDER BY id DESC LIMIT 1"
        cursor.execute(query)
        last_row = cursor.fetchone()
        return last_row[0]
    

@app.get("/tasks")
async def get_tasks():
    """READS TASKS FROM DATABASE"""
    if not global_user_id:
        return {"No Login yet"}
    cursor = DATABASE_URL.cursor()
    query = "SELECT * FROM tasks"
    cursor.execute(query)
    result = cursor.fetchall()
    result_list = []
    column_names = [desc[0] for desc in cursor.description]
    for row in result:
        result_list.append(dict(zip(column_names, row)))
    result_json = json.dumps(result_list)
    return result_json

@app.post("/tasks")
async def create_task(taskModel: Task):
    """TASK CREATION END POINT"""
    global global_user_id
    if not global_user_id:
        return {"message": "Login Before Creating Tasks"}
    task_id = await TaskMethods.create_task(taskModel)
    if task_id:
        return {"id": task_id, "message": "Task created successfully"}
    else:
        return {"message": "Task creation failed"}

@app.put("/tasks/{task_id}")
async def update_task(task_id: int, task: Task):
    """TASK UPDATING ENDPOINT"""
    if not global_user_id:
        return {"Login First"}
    cursor = DATABASE_URL.cursor()
    query = "UPDATE tasks SET title=%s, description=%s, status=%s WHERE id=%s"
    result = cursor.execute(query, (task.title, task.description, task.status, task_id))
    conn.commit()
    if not result:
        raise HTTPException(status_code=400, detail="Task not found")
    return {"message": "Task updated successfully"}

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    """TASK DELETING ENDPOINT"""
    if not global_user_id:
        return {"Login First"}
    query = "DELETE FROM tasks WHERE id=%s;"
    cursor = DATABASE_URL.cursor()
    result = cursor.execute(query,(task_id))
    conn.commit()
    if not result:
        raise HTTPException(status_code=400, detail="Task not found")
    return {"message": "Task deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)