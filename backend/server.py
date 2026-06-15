"""
英语刷题系统 - 后端 API 服务 (FastAPI)
前后端分离后，前端通过 HTTP 调用本服务操作数据库
"""
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import db as db_module

app = FastAPI(title='英语刷题系统 API', version='1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ========== 简单 Token 鉴权（本地应用） ==========
_tokens: dict[str, int] = {}  # token -> user_id

def _gen_token() -> str:
    return uuid.uuid4().hex[:32]

# ========== Pydantic 请求模型 ==========

class LoginReq(BaseModel):
    username: str
    password: str

class RegisterReq(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = None

class AnswerReq(BaseModel):
    user_id: int
    question_id: int
    user_answer: str
    is_correct: bool
    score: float
    practice_id: Optional[int] = None

class ScoreReq(BaseModel):
    user_id: int
    question_id: int
    score: float
    practice_id: Optional[int] = None

class KnowledgeReq(BaseModel):
    user_id: int
    question_id: int
    is_correct: bool

class NoteReq(BaseModel):
    user_id: int
    content: str = ''
    note_type: str = 'text'
    image_path: Optional[str] = None
    question_id: Optional[int] = None

class NoteUpdateReq(BaseModel):
    user_id: int
    content: Optional[str] = None
    note_type: Optional[str] = None
    image_path: Optional[str] = None

# ========== 用户 ==========

@app.post('/api/login')
def login(req: LoginReq):
    success, user, msg = db_module.login_user(req.username, req.password)
    if not success:
        raise HTTPException(400, msg)
    token = _gen_token()
    _tokens[token] = user['id']
    return {'success': True, 'token': token, 'user': user, 'msg': msg}

@app.post('/api/register')
def register(req: RegisterReq):
    success, uid, msg = db_module.register_user(req.username, req.password, req.nickname)
    if not success:
        raise HTTPException(400, msg)
    return {'success': True, 'user_id': uid, 'msg': msg}

# ========== 题目 ==========

@app.get('/api/questions/random')
def get_random_questions(count: Optional[int] = None, question_type: Optional[str] = None):
    return db_module.get_random_questions(count=count, question_type=question_type)

@app.get('/api/questions/{question_id}')
def get_question_by_id(question_id: int):
    q = db_module.get_question_by_id(question_id)
    if not q:
        raise HTTPException(404, '题目不存在')
    return q

@app.get('/api/questions/{parent_id}/children')
def get_child_questions(parent_id: int):
    return db_module.get_child_questions(parent_id)

# ========== 练习记录 ==========

@app.post('/api/practice')
def create_practice(user_id: int):
    pid = db_module.create_practice_record(user_id)
    if pid is None:
        raise HTTPException(500, '创建练习记录失败')
    return {'practice_id': pid}

@app.put('/api/practice/{practice_id}/finish')
def finish_practice(practice_id: int, total: int, correct: int, score: float):
    db_module.finish_practice_record(practice_id, total, correct, score)
    return {'success': True}

# ========== 答题记录 ==========

@app.post('/api/answers')
def save_answer(req: AnswerReq):
    ok = db_module.save_answer_record(
        req.user_id, req.question_id, req.user_answer,
        req.is_correct, req.score, req.practice_id
    )
    if not ok:
        raise HTTPException(500, '保存答题记录失败')
    return {'success': True}

@app.put('/api/answers/score')
def update_answer_score(req: ScoreReq):
    """更新作文/翻译的自评分数"""
    conn = db_module.get_conn()
    cur = conn.cursor()
    try:
        if req.practice_id:
            cur.execute("""
                UPDATE answer_records SET score = %s
                WHERE user_id = %s AND question_id = %s AND practice_id = %s
            """, (req.score, req.user_id, req.question_id, req.practice_id))
        else:
            cur.execute("""
                UPDATE answer_records SET score = %s
                WHERE user_id = %s AND question_id = %s AND score = 0
                ORDER BY answered_at DESC LIMIT 1
            """, (req.score, req.user_id, req.question_id))
        conn.commit()
        return {'success': True}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f'更新分数失败: {e}')
    finally:
        cur.close()
        conn.close()

# ========== 错题本 ==========

@app.get('/api/wrong-answers')
def get_wrong_answers(user_id: int, limit: int = 50):
    return db_module.get_wrong_answers(user_id, limit)

# ========== 数据分析 ==========

@app.get('/api/stats')
def get_user_stats(user_id: int):
    return db_module.get_user_stats(user_id)

# ========== 知识点进度 ==========

@app.post('/api/knowledge-progress')
def update_knowledge_progress(req: KnowledgeReq):
    db_module.update_knowledge_progress(req.user_id, req.question_id, req.is_correct)
    return {'success': True}

# ========== 笔记本 ==========

@app.get('/api/notebook-pages')
def get_notebook_pages(user_id: int):
    return db_module.get_notebook_pages(user_id)

@app.post('/api/notebook-pages')
def add_notebook_page(req: NoteReq):
    success, page_order, msg = db_module.add_notebook_page(
        req.user_id, req.content, req.note_type, req.image_path, req.question_id
    )
    if not success:
        raise HTTPException(500, msg)
    return {'success': True, 'page_order': page_order, 'msg': msg}

@app.put('/api/notebook-pages/{page_id}')
def update_notebook_page(page_id: int, req: NoteUpdateReq):
    success = db_module.update_notebook_page(
        page_id, req.user_id, req.content, req.note_type, req.image_path
    )
    if not success:
        raise HTTPException(500, '更新失败')
    return {'success': True}

@app.delete('/api/notebook-pages/{page_id}')
def delete_notebook_page(page_id: int, user_id: int):
    success = db_module.delete_notebook_page(user_id, page_id)
    if not success:
        raise HTTPException(500, '删除失败')
    return {'success': True}

# ========== 笔记（题目标注）==========

@app.get('/api/notes')
def get_notes(user_id: int, limit: int = 50):
    return db_module.get_notes(user_id, limit)

@app.post('/api/notes')
def save_note(req: NoteReq):
    success, msg = db_module.save_note(
        req.user_id, req.question_id, req.content, req.note_type, req.image_path
    )
    if not success:
        raise HTTPException(500, msg)
    return {'success': True, 'msg': msg}

# ========== 启动入口 ==========

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8765)
