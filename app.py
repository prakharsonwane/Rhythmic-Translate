import os, io, sqlite3
from pathlib import Path
from datetime import datetime
from functools import wraps
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

load_dotenv()
BASE = Path(__file__).resolve().parent
(BASE / 'instance').mkdir(exist_ok=True)
DB = BASE / 'instance' / 'rhythmic_translate.db'
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-development-secret')
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024
LANGS = {'auto':'Auto-detect','en':'English','hi':'Hindi','es':'Spanish','fr':'French','de':'German','it':'Italian','pt':'Portuguese','ru':'Russian','ja':'Japanese','ko':'Korean','zh':'Chinese','ar':'Arabic','bn':'Bengali','ur':'Urdu','mr':'Marathi','ta':'Tamil','te':'Telugu','gu':'Gujarati','pa':'Punjabi','nl':'Dutch','tr':'Turkish','id':'Indonesian','th':'Thai','vi':'Vietnamese','pl':'Polish','uk':'Ukrainian','sv':'Swedish'}
ALLOWED = {'.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff','.pdf','.txt','.docx'}

def connect_db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON'); return c

with connect_db() as c:
    c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS translations(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, source_text TEXT NOT NULL, translated_text TEXT NOT NULL, source_lang TEXT NOT NULL, target_lang TEXT NOT NULL, is_favorite INTEGER DEFAULT 0, created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)')

def current_user():
    if not session.get('user_id'): return None
    with connect_db() as c: return c.execute('SELECT id,username,email FROM users WHERE id=?', (session['user_id'],)).fetchone()

@app.context_processor
def template_globals(): return {'current_user': current_user(), 'languages': LANGS}

def signed_in(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash('Sign in to use your personal history.', 'info')
            return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapper

@app.route('/')
def index(): return render_template('index.html')
@app.route('/about')
def about(): return render_template('about.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        name=request.form.get('username','').strip(); email=request.form.get('email','').strip().lower(); pw=request.form.get('password','')
        if len(name)<3 or '@' not in email or len(pw)<8:
            flash('Use a 3+ character username, valid email and password of at least 8 characters.', 'error')
        else:
            try:
                with connect_db() as c:
                    cur=c.execute('INSERT INTO users(username,email,password_hash,created_at) VALUES(?,?,?,?)',(name,email,generate_password_hash(pw),datetime.utcnow().isoformat(timespec='seconds')))
                session.clear(); session['user_id']=cur.lastrowid; flash('Account created!', 'success'); return redirect(url_for('index'))
            except sqlite3.IntegrityError: flash('That username or email is already registered.', 'error')
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        ident=request.form.get('identity','').strip().lower(); pw=request.form.get('password','')
        with connect_db() as c: u=c.execute('SELECT * FROM users WHERE lower(username)=? OR lower(email)=?',(ident,ident)).fetchone()
        if u and check_password_hash(u['password_hash'],pw):
            session.clear(); session['user_id']=u['id']; nxt=request.args.get('next','')
            return redirect(nxt if nxt.startswith('/') and not nxt.startswith('//') else url_for('index'))
        flash('Incorrect username/email or password.', 'error')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout(): session.clear(); return redirect(url_for('index'))

def translate_text(text, src, dst, mode):
    if not text.strip(): raise ValueError('Enter text to translate.')
    if len(text)>4500: raise ValueError('Please keep text under 4,500 characters.')
    if src == dst: return text, 'No translation needed'
    if mode == 'ai':
        key=os.getenv('OPENAI_API_KEY','')
        if not key: raise ValueError('AI mode needs OPENAI_API_KEY in .env. Standard mode works without it.')
        r=requests.post('https://api.openai.com/v1/chat/completions',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},json={'model':os.getenv('OPENAI_MODEL','gpt-4o-mini'),'messages':[{'role':'system','content':'Translate faithfully into the requested target language. Preserve meaning and formatting. Return only the translation.'},{'role':'user','content':f"From {LANGS.get(src,src)} to {LANGS.get(dst,dst)}:\n{text}"}],'temperature':0.2},timeout=45)
        if r.status_code>=400: raise ValueError('AI service error. Check your API key and model.')
        return r.json()['choices'][0]['message']['content'].strip(), 'AI translation'
    r=requests.get('https://api.mymemory.translated.net/get',params={'q':text,'langpair':f"{'autodetect' if src=='auto' else src}|{dst}"},timeout=25); r.raise_for_status(); data=r.json()
    result=(data.get('responseData') or {}).get('translatedText','').strip()
    if not result or data.get('responseStatus') not in (200,'200'): raise ValueError('Translation service returned no result. Try again.')
    return result, 'Standard translation'

@app.route('/api/translate', methods=['POST'])
def api_translate():
    if not session.get('user_id'): return jsonify(error='Create an account or log in to translate.'),401
    p=request.get_json(silent=True) or {}
    if not isinstance(p, dict): return jsonify(error='Invalid request body. Please retry.'),400
    raw_text=p.get('text','')
    if not isinstance(raw_text, str): return jsonify(error='Text must be plain text.'),400
    text=raw_text; src=p.get('source_lang','auto'); dst=p.get('target_lang','hi'); mode=p.get('mode','standard')
    if not isinstance(src, str) or not isinstance(dst, str) or src not in LANGS or dst not in LANGS or dst=='auto':
        return jsonify(error='Choose valid source and target languages.'),400
    if mode not in ('standard','ai'): mode='standard'
    try:
        out,provider=translate_text(text,src,dst,mode)
        if session.get('user_id'):
            with connect_db() as c: c.execute('INSERT INTO translations(user_id,source_text,translated_text,source_lang,target_lang,created_at) VALUES(?,?,?,?,?,?)',(session['user_id'],text,out,src,dst,datetime.utcnow().isoformat(timespec='seconds')))
        return jsonify(translated_text=out,provider=provider,saved=bool(session.get('user_id')))
    except ValueError as e: return jsonify(error=str(e)),400
    except requests.RequestException: return jsonify(error='Translation service is temporarily unavailable. Please retry in a moment.'),502

def extract_ocr(data, name, mime):
    key=os.getenv('OCR_SPACE_API_KEY','')
    if not key: raise ValueError('Image OCR needs OCR_SPACE_API_KEY in .env.')
    r=requests.post('https://api.ocr.space/parse/image',data={'apikey':key,'language':'eng'},files={'file':(name,data,mime)},timeout=60); r.raise_for_status(); j=r.json()
    if j.get('IsErroredOnProcessing'): raise ValueError('OCR could not read this file; try a clearer image.')
    text='\n'.join(x.get('ParsedText','') for x in j.get('ParsedResults',[])).strip()
    if not text: raise ValueError('No readable text found.')
    return text

@app.route('/api/extract', methods=['POST'])
def extract_file():
    if not session.get('user_id'): return jsonify(error='Create an account or log in to use file and camera OCR.'),401
    f=request.files.get('file')
    if not f: return jsonify(error='Choose a file first.'),400
    name=secure_filename(f.filename or ''); ext=Path(name).suffix.lower(); data=f.read()
    if ext not in ALLOWED: return jsonify(error='Supported files: images, PDF, TXT and DOCX.'),400
    try:
        if ext=='.txt': text=data.decode('utf-8',errors='replace')
        elif ext=='.docx':
            from docx import Document
            text='\n'.join(p.text for p in Document(io.BytesIO(data)).paragraphs if p.text.strip())
        elif ext=='.pdf':
            import fitz
            doc=fitz.open(stream=data,filetype='pdf'); text='\n'.join(p.get_text() for p in doc).strip()
            if not text: text=extract_ocr(data,name,'application/pdf')
        else: text=extract_ocr(data,name,f.mimetype or 'application/octet-stream')
        if not text.strip(): raise ValueError('No text found in this file.')
        return jsonify(text=text[:20000],filename=name)
    except ValueError as e: return jsonify(error=str(e)),400
    except Exception: return jsonify(error='Could not read file. Scanned PDFs/images need a working OCR API key.'),400

@app.route('/history')
@signed_in
def history():
    q=request.args.get('q','').strip()[:100]; fav=request.args.get('favorites')=='1'; sql='SELECT * FROM translations WHERE user_id=?'; args=[session['user_id']]
    if q: sql+=' AND (source_text LIKE ? OR translated_text LIKE ?)'; args += [f'%{q}%',f'%{q}%']
    if fav: sql+=' AND is_favorite=1'
    sql+=' ORDER BY id DESC LIMIT 250'
    with connect_db() as c: rows=c.execute(sql,args).fetchall()
    return render_template('history.html',rows=rows,q=q,favorites_only=fav)
@app.route('/history/<int:item>/favorite',methods=['POST'])
@signed_in
def favorite(item):
    with connect_db() as c: c.execute('UPDATE translations SET is_favorite=1-is_favorite WHERE id=? AND user_id=?',(item,session['user_id']))
    return redirect(request.referrer or url_for('history'))
@app.route('/history/<int:item>/delete',methods=['POST'])
@signed_in
def delete(item):
    with connect_db() as c: c.execute('DELETE FROM translations WHERE id=? AND user_id=?',(item,session['user_id']))
    return redirect(url_for('history'))
@app.route('/history/clear',methods=['POST'])
@signed_in
def clear_history():
    with connect_db() as c: c.execute('DELETE FROM translations WHERE user_id=?',(session['user_id'],))
    return redirect(url_for('history'))
@app.route('/history/<int:item>/download')
@signed_in
def download(item):
    with connect_db() as c: row=c.execute('SELECT * FROM translations WHERE id=? AND user_id=?',(item,session['user_id'])).fetchone()
    if not row: return redirect(url_for('history'))
    body=f"Rhythmic Translate\n\nSource ({row['source_lang']}):\n{row['source_text']}\n\nTranslation ({row['target_lang']}):\n{row['translated_text']}\n"
    return send_file(io.BytesIO(body.encode()),as_attachment=True,download_name=f'translation-{item}.txt',mimetype='text/plain')
@app.errorhandler(413)
def too_large(e): return jsonify(error='File is too large (maximum 12 MB).'),413
if __name__=='__main__': app.run(debug=os.getenv('FLASK_DEBUG','0')=='1')
