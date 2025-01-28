from upstash_redis import Redis
import os
import json
from datetime import datetime, timedelta
import uuid

# Initialize Redis client with Upstash instead of local Redis
redis = Redis(
    url="https://proven-warthog-57623.upstash.io",
    token="AeEXAAIjcDExOWJiMzhkOTZkMTI0ODE4YjI5NWFhMzUyMDkxZTEwY3AxMA"
)

class BBSService:
    @staticmethod
    def verify_user(handle, password):
        user_data = redis.hget('bbs:users', handle.lower())
        if user_data:
            user = json.loads(user_data)
            if user['password'] == password:  # Simple password comparison for development
                BBSService.update_user_stats(handle)
                return user
        return None

    @staticmethod
    def save_user(handle, password):
        user = {
            'handle': handle.lower(),
            'password': password,
            'access_level': 10 if handle.lower() == 'sysop' else 0,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'login_count': 0,
            'post_count': 0
        }
        redis.hset('bbs:users', handle.lower(), json.dumps(user))

    @staticmethod
    def update_user_stats(handle):
        user_data = redis.hget('bbs:users', handle.lower())
        if user_data:
            user = json.loads(user_data)
            user['last_login'] = datetime.now().isoformat()
            user['login_count'] += 1
            redis.hset('bbs:users', handle.lower(), json.dumps(user))
            # Update global stats
            redis.hincrby('bbs:global_stats', 'total_calls', 1)
            redis.hincrby('bbs:global_stats', 'today_calls', 1)
            redis.hset('bbs:global_stats', 'last_caller', handle)

    @staticmethod
    async def get_message_boards():
        boards = redis.hgetall('bbs:boards')
        return {
            'public': [b for b in boards.values() if json.loads(b)['access_level'] <= 0],
            'private': [b for b in boards.values() if json.loads(b)['access_level'] > 0]
        }

    @staticmethod
    async def create_post(handle, board_id, content):
        post_id = f"post:{uuid.uuid4()}"
        post = {
            'handle': handle,
            'board_id': board_id,
            'content': content,
            'timestamp': int(datetime.now().timestamp())
        }
        redis.hset(f'bbs:board:{board_id}', post_id, json.dumps(post))
        redis.expire(f'bbs:board:{board_id}', 60 * 60 * 24 * 30)  # 30 days TTL
        # Update user post count
        user_data = redis.hget('bbs:users', handle.lower())
        if user_data:
            user = json.loads(user_data)
            user['post_count'] += 1
            redis.hset('bbs:users', handle.lower(), json.dumps(user))

    @staticmethod
    async def get_posts(board_id):
        posts = redis.hgetall(f'bbs:board:{board_id}')
        return sorted(
            [json.loads(p) for p in posts.values()],
            key=lambda x: x['timestamp'],
            reverse=True
        )

    @staticmethod
    async def get_system_stats():
        stats = redis.hgetall('bbs:global_stats')
        active_users = redis.hkeys('bbs:active_sessions')
        return {
            'users_online': len(active_users),
            'calls_today': int(stats.get('today_calls', 0)),
            'last_caller': stats.get('last_caller', 'None')
        }

    @staticmethod
    def track_session(handle):
        session = {
            'handle': handle,
            'connect_time': datetime.now().isoformat(),
            'last_active': datetime.now().isoformat()
        }
        redis.hset('bbs:active_sessions', handle, json.dumps(session))
        redis.expire(f'bbs:active_sessions:{handle}', 60 * 60 * 2)  # 2 hours TTL

    @staticmethod
    async def cleanup_expired_sessions():
        sessions = redis.hgetall('bbs:active_sessions')
        now = datetime.now()
        for handle, session_data in sessions.items():
            session = json.loads(session_data)
            last_active = datetime.fromisoformat(session['last_active'])
            if (now - last_active).total_seconds() > 7200:  # 2 hours
                redis.hdel('bbs:active_sessions', handle)

    @staticmethod
    async def get_post_with_quote(post_id):
        # Get post from Redis
        board_keys = redis.keys('bbs:board:*')
        for board_key in board_keys:
            post_data = redis.hget(board_key, f"post:{post_id}")
            if post_data:
                post = json.loads(post_data)
                board_name = redis.hget('bbs:boards', post['board_id'])
                board_info = json.loads(board_name) if board_name else {'name': 'Unknown'}
                
                quoted = f"> {board_info['name']} - {post['handle']} wrote:\n"
                quoted += '\n'.join([f"> {line}" for line in post['content'].split('\n')])
                return quoted
        return None

    @staticmethod
    async def format_rfc822(post):
        return f'''From: {post['handle']}
Newsgroups: {post['board_id']}
Date: {post['timestamp']}
Message-ID: <{post['id']}@bbs.dohmboy64.com>

{post['content']}
'''

    @staticmethod
    async def generate_ansi_thumbnail(ansi_file):
        return ansi_file[:100] + '...'  # Simple preview

    @staticmethod
    async def validate_session(session_id):
        session_data = redis.hget('bbs:sessions', session_id)
        if not session_data:
            return None
        return json.loads(session_data)

    @staticmethod
    async def create_session(user):
        session_id = str(uuid.uuid4())
        redis.hset('bbs:sessions', session_id, json.dumps({
            'handle': user['handle'],
            'access_level': user['access_level'],
            'expires': (datetime.now() + timedelta(hours=2)).isoformat()
        }))
        redis.expire(f'bbs:sessions:{session_id}', 7200)  # 2 hours
        return session_id

    @staticmethod
    def init_app(app, socketio):
        """Initialize BBS service with app and socketio instances"""
        from routes.bbs_routes import register_socketio_events
        
        # Register BBS blueprint
        from routes.bbs_routes import bbs
        app.register_blueprint(bbs, url_prefix='/bbs')
        
        # Register socket events
        register_socketio_events(socketio)
        
        # Setup cleanup task
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(BBSService.cleanup_expired_sessions, 'interval', hours=1)
        scheduler.start() 