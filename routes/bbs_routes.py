from flask import Blueprint, request, jsonify, g, render_template, Response
from flask_socketio import join_room, leave_room, emit
from services.bbs_service import BBSService, redis
from datetime import datetime
import json
from routes.image_routes import upload_to_vercel_blob  # Reuse blob util
import uuid
from os.path import splitext  # Only need splitext for file extensions
import asyncio
from queue import Queue
from threading import Event
import time

bbs = Blueprint('bbs', __name__)

# Message queue for each chat room
chat_messages = Queue()
connected_clients = set()

@bbs.route('/bbs')
async def bbs_home():
    return render_template('bbs.html')

@bbs.route('/bbs/login', methods=['POST'])
def bbs_login():
    data = request.get_json()
    # Check if handle exists first
    user_data = redis.hget('bbs:users', data['handle'].lower())
    if not user_data:
        return jsonify({'error': 'Invalid credentials'}), 401
        
    user = json.loads(user_data)
    if user['password'] == data['password']:
        BBSService.track_session(data['handle'])
        return jsonify({
            'handle': data['handle'],
            'accessLevel': user['access_level']
        })
    return jsonify({'error': 'Invalid credentials'}), 401

@bbs.route('/bbs/register', methods=['POST'])
def bbs_register():
    data = request.get_json()
    if len(data['handle']) < 3:
        return jsonify({'error': 'Handle too short'}), 400
        
    # Check if handle exists
    existing_user = redis.hget('bbs:users', data['handle'].lower())
    if existing_user:
        return jsonify({'error': 'Handle already taken'}), 400
        
    # Create new user
    BBSService.save_user(data['handle'], data['password'])
    return jsonify({'status': 'Registered'})

@bbs.route('/bbs/files/<category>/<subcategory>/<filename>')
async def serve_bbs_file(category, subcategory, filename):
    file_key = f"bbs:files:{category}:{subcategory}:{filename}"
    file_data = await redis.hget(f"bbs:files:{category}", filename)
    if file_data:
        file_info = json.loads(file_data)
        return jsonify(file_info)
    return jsonify({'error': 'File not found'}), 404

@bbs.route('/bbs/posts', methods=['POST'])
async def create_message_post():
    data = request.get_json()
    try:
        board = await redis.hget('bbs:boards', data['board_id'])
        if not board:
            return jsonify({'error': 'Board not found'}), 404
        user = await redis.hget('bbs:users', data['handle'].lower())
        if not user:
            return jsonify({'error': 'User not found'}), 404
        await BBSService.create_post(
            handle=data['handle'],
            board_id=data['board_id'],
            content=data['content']
        )
        return jsonify({'status': 'Post created'})
    except KeyError:
        return jsonify({'error': 'Missing required fields'}), 400

@bbs.route('/bbs/posts/<board_id>', methods=['GET'])
async def get_board_posts(board_id):
    board = await redis.hget('bbs:boards', board_id)
    if not board:
        return jsonify({'error': 'Board not found'}), 404
    posts = await BBSService.get_posts(board_id)
    return jsonify(posts)

@bbs.route('/bbs/stats/<handle>')
async def get_user_statistics(handle):
    # Verify user exists before getting stats
    user = await redis.hget('bbs:users', handle.lower())
    if not user:
        return jsonify({'error': 'User not found'}), 404
    stats = await BBSService.get_user_stats(handle)
    return jsonify(stats)

@bbs.route('/bbs/art')
async def browse_art_gallery():
    art_files = await redis.hgetall('bbs:art_files')
    return jsonify({'artworks': [json.loads(f) for f in art_files.values()]})

@bbs.route('/bbs/art/<filename>')
async def serve_art_file(filename):
    art_file = await redis.hget('bbs:art_files', filename)
    if art_file:
        file_data = json.loads(art_file)
        await redis.expire('bbs:art_files', 60 * 60 * 24 * 30)  # 30 days
        return jsonify(file_data)
    return jsonify({'error': 'File not found'}), 404

@bbs.route('/bbs/archive/<category>')
async def get_file_archive(category):
    # Verify category exists
    if not await redis.hexists('bbs:categories', category):
        return jsonify({'error': 'Invalid category'}), 404
    files = await redis.hgetall(f'bbs:files:{category}')
    return jsonify([json.loads(f) for f in files.values()])

@bbs.route('/bbs/stats')
async def get_bbs_stats():
    stats = await BBSService.get_system_stats()
    return jsonify(stats)

@bbs.route('/bbs/boards')
async def get_message_boards():
    boards = await BBSService.get_message_boards()
    return jsonify(boards)

@bbs.route('/bbs/upload', methods=['POST'])
async def upload_bbs_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if not allowed_bbs_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        # Verify user exists before allowing upload
        user = await redis.hget('bbs:users', g.user['handle'].lower())
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify category exists
        if not await redis.hexists('bbs:categories', request.form['category']):
            return jsonify({'error': 'Invalid category'}), 400

        blob_url = upload_to_vercel_blob(
            file.read(),
            f"bbs_{uuid.uuid4().hex}{splitext(file.filename)[1]}",
            file.content_type
        )
        
        file_info = {
            'filename': file.filename,
            'blob_url': blob_url,
            'category': request.form['category'],
            'uploader': g.user['handle'],
            'uploaded_at': datetime.now().isoformat()
        }
        await redis.hset(
            f"bbs:files:{request.form['category']}", 
            file.filename, 
            json.dumps(file_info)
        )
        await redis.expire(f"bbs:files:{request.form['category']}", 60 * 60 * 24 * 30)
        
        return jsonify({'url': blob_url})
    
    except Exception as e:
        print(f"BBS upload error: {str(e)}")  # Simple print for now
        return jsonify({'error': 'Upload failed'}), 500

def allowed_bbs_file(filename):
    return '.' in filename and \
        splitext(filename)[1].lower()[1:] in {'txt','ans','png','jpg','jpeg'}

# WebSocket events using existing SocketIO instance
def register_socketio_events(socketio):
    @socketio.on('bbs_chat_join', namespace='/bbs_chat')
    async def handle_join(data):
        join_room('bbs_chat')
        await BBSService.track_session(data['handle'])
        users = await redis.hkeys('bbs:active_sessions')
        emit('bbs_chat_update', {
            'users': list(users),
            'message': f"{data['handle']} entered chat"
        }, room='bbs_chat')

    @socketio.on('bbs_chat_message', namespace='/bbs_chat')
    async def handle_message(data):
        emit('bbs_chat_message', {
            'from': data['handle'],
            'message': data['message'],
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }, room='bbs_chat')

    @socketio.on('disconnect', namespace='/bbs_chat')
    async def handle_leave():
        sessions = await redis.hgetall('bbs:active_sessions')
        for handle, session_data in sessions.items():
            session = json.loads(session_data)
            if session['handle'] == request.sid:
                await redis.hdel('bbs:active_sessions', handle)
                users = await redis.hkeys('bbs:active_sessions')
                emit('bbs_chat_update', {
                    'users': list(users),
                    'message': f"{handle} left chat"
                }, room='bbs_chat')
                break 

@bbs.route('/bbs/chat/send', methods=['POST'])
def send_chat_message():
    data = request.get_json()
    message = {
        'from': data['handle'],
        'message': data['message'],
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }
    # Store message in Redis with TTL (non-async)
    redis.lpush('bbs:chat:messages', json.dumps(message))
    redis.ltrim('bbs:chat:messages', 0, 99)  # Keep last 100 messages
    redis.expire('bbs:chat:messages', 60 * 60 * 24)  # 24 hour TTL
    
    # Update active users
    BBSService.track_session(data['handle'])
    return jsonify({'status': 'sent'})

@bbs.route('/bbs/chat/stream')
def stream_chat():
    # Get client_id from request before entering generator
    client_id = request.headers.get('Client-ID')
    connected_clients.add(client_id)

    def generate():
        try:
            last_id = 0
            while True:
                # Get new messages from Redis (non-async)
                messages = redis.lrange('bbs:chat:messages', 0, -1)
                active_users = redis.hkeys('bbs:active_sessions')
                
                if messages:
                    for msg in messages[last_id:]:
                        yield f"data: {msg}\n\n"
                    last_id = len(messages)
                
                # Send active users update
                users_data = {
                    'type': 'users_update',
                    'users': list(active_users)
                }
                yield f"data: {json.dumps(users_data)}\n\n"
                
                time.sleep(1)
        except GeneratorExit:
            connected_clients.remove(client_id)
            
    return Response(generate(), mimetype='text/event-stream')

@bbs.route('/bbs/chat/users')
def get_active_users():  # Remove async
    active_users = redis.hkeys('bbs:active_sessions')  # Remove await
    return jsonify(list(active_users)) 