import asyncio
import json
import os
import uuid
import time
import random
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from flask import Flask, render_template, request, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import socket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Rate limiting classes
class RateLimiter:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    def is_allowed(self):
        now = time.time()
        # Remove old requests outside the time window
        while self.requests and self.requests[0] <= now - self.time_window:
            self.requests.popleft()
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
    
    def get_reset_time(self):
        if not self.requests:
            return 0
        return self.requests[0] + self.time_window

class IPRateLimiter:
    def __init__(self):
        self.limiters = {}
        self.blocked_ips = {}
        self.excessive_ips = {}
        self.rate_limit_notifications = defaultdict(int)
        self.config = self.load_config()
    
    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "rate_limit_global": "30:5",
                "rate_limit_per_ip": "3:30",
                "rate_limit_global_block_for": "120",
                "rate_limit_per_ip_block_for": "120",
                "rate_limit_excessive": "5:60",
                "rate_limit_excessive_block_for": "600"
            }
    
    def parse_rate_limit(self, rate_str):
        """Parse rate limit string like '30:5' into (max_requests, time_window)"""
        max_requests, time_window = rate_str.split(':')
        return int(max_requests), int(time_window)
    
    def is_ip_whitelisted(self, ip):
        try:
            with open('access/white_list.json', 'r') as f:
                whitelist = json.load(f)
                return ip in whitelist
        except (FileNotFoundError, json.JSONDecodeError):
            return False
    
    def is_ip_blacklisted(self, ip):
        try:
            with open('access/black_list.json', 'r') as f:
                blacklist = json.load(f)
                return ip in blacklist
        except (FileNotFoundError, json.JSONDecodeError):
            return False
    
    def is_ip_blocked(self, ip):
        if self.is_ip_whitelisted(ip):
            return False
        
        if self.is_ip_blacklisted(ip):
            return True
        
        # Check if IP is temporarily blocked
        if ip in self.blocked_ips:
            if time.time() < self.blocked_ips[ip]:
                return True
            else:
                del self.blocked_ips[ip]
        
        return False
    
    def check_rate_limit(self, ip):
        if self.is_ip_whitelisted(ip):
            return True, None
        
        if self.is_ip_blacklisted(ip):
            return False, "IP address is blacklisted"
        
        if self.is_ip_blocked(ip):
            return False, "IP address is temporarily blocked"
        
        # Check global rate limit
        global_max, global_window = self.parse_rate_limit(self.config["rate_limit_global"])
        if not hasattr(self, 'global_limiter'):
            self.global_limiter = RateLimiter(global_max, global_window)
        
        if not self.global_limiter.is_allowed():
            # Global rate limit hit - block all IPs temporarily
            global_block_duration = int(self.config["rate_limit_global_block_for"])
            self.blocked_ips[ip] = time.time() + global_block_duration
            
            # Check if this IP should be marked as excessive
            self.rate_limit_notifications[ip] += 1
            excessive_max, excessive_window = self.parse_rate_limit(self.config["rate_limit_excessive"])
            
            if self.rate_limit_notifications[ip] > excessive_max:
                excessive_block_duration = int(self.config["rate_limit_excessive_block_for"])
                self.excessive_ips[ip] = time.time() + excessive_block_duration
                # Add to blacklist for excessive usage
                add_to_blacklist(ip, f"Excessive rate limiting: {self.rate_limit_notifications[ip]} hits in {excessive_window}s")
                
                # Emit excessive rate limit notification to admins
                socketio.emit('admin_action_notification', {
                    'action': 'excessive_rate_limit',
                    'message': f'IP {ip} has been blacklisted for excessive rate limiting ({self.rate_limit_notifications[ip]} hits in {excessive_window}s)',
                    'timestamp': datetime.now().isoformat()
                }, room='admin')
                
                return False, "Rate limit exceeded - excessive usage detected"
            
            return False, "Global rate limit exceeded - temporary block applied"
        
        # Check per-IP rate limit
        per_ip_max, per_ip_window = self.parse_rate_limit(self.config["rate_limit_per_ip"])
        if ip not in self.limiters:
            self.limiters[ip] = RateLimiter(per_ip_max, per_ip_window)
        
        if not self.limiters[ip].is_allowed():
            per_ip_block_duration = int(self.config["rate_limit_per_ip_block_for"])
            self.blocked_ips[ip] = time.time() + per_ip_block_duration
            
            # Check if this IP should be marked as excessive
            self.rate_limit_notifications[ip] += 1
            excessive_max, excessive_window = self.parse_rate_limit(self.config["rate_limit_excessive"])
            
            if self.rate_limit_notifications[ip] > excessive_max:
                excessive_block_duration = int(self.config["rate_limit_excessive_block_for"])
                self.excessive_ips[ip] = time.time() + excessive_block_duration
                # Add to blacklist for excessive usage
                add_to_blacklist(ip, f"Excessive rate limiting: {self.rate_limit_notifications[ip]} hits in {excessive_window}s")
                
                # Emit excessive rate limit notification to admins
                socketio.emit('admin_action_notification', {
                    'action': 'excessive_rate_limit',
                    'message': f'IP {ip} has been blacklisted for excessive rate limiting ({self.rate_limit_notifications[ip]} hits in {excessive_window}s)',
                    'timestamp': datetime.now().isoformat()
                }, room='admin')
                
                return False, "Rate limit exceeded - excessive usage detected"
            
            return False, "Rate limit exceeded for this IP"
        
        return True, None

# Initialize rate limiter
rate_limiter = IPRateLimiter()

# Global state
current_question = None
current_comment = None
admin_sessions = set()
browser_admin_sessions = {}  # Map browser_id -> session_id for admin tracking
pending_comments = []
current_video_source = 'https://www.youtube.com/embed/dQw4w9WgXcQ'

# Giveaway system
giveaways = []
active_giveaways = []
giveaway_timers = {}
giveaway_winners = {}  # Track winners per IP
connected_clients = set()  # Track connected clients for winner selection
admin_connected_clients = set()  # Track which connected clients are admins

def get_local_ip():
    """Get the local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_client_ip():
    """Get the client IP address from request"""
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        ip = request.remote_addr
    
    # For localhost testing, use IP + User-Agent to distinguish clients
    user_agent = request.headers.get('User-Agent', '')
    if ip in ['127.0.0.1', '::1', 'localhost']:
        # Create a unique identifier for localhost clients
        import hashlib
        unique_id = hashlib.md5(f"{ip}_{user_agent}".encode()).hexdigest()[:8]
        return f"{ip}_{unique_id}"
    
    return ip

def add_to_whitelist(ip, reason=""):
    """Add IP to whitelist"""
    try:
        with open('access/white_list.json', 'r') as f:
            whitelist = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        whitelist = []
    
    if ip not in whitelist:
        whitelist.append({
            'ip': ip,
            'added_at': datetime.now().isoformat(),
            'reason': reason
        })
        with open('access/white_list.json', 'w') as f:
            json.dump(whitelist, f, indent=2)
        return True
    return False

def add_to_blacklist(ip, reason=""):
    """Add IP to blacklist"""
    try:
        with open('access/black_list.json', 'r') as f:
            blacklist = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        blacklist = []
    
    if ip not in blacklist:
        blacklist.append({
            'ip': ip,
            'added_at': datetime.now().isoformat(),
            'reason': reason
        })
        with open('access/black_list.json', 'w') as f:
            json.dump(blacklist, f, indent=2)
        return True
    return False

def check_auto_acl(ip, action_type, is_accepted):
    """Check if IP should be auto-whitelisted or blacklisted"""
    config = rate_limiter.config
    
    # Skip if IP is already whitelisted
    if rate_limiter.is_ip_whitelisted(ip):
        return
    
    # Skip if IP is already blacklisted
    if rate_limiter.is_ip_blacklisted(ip):
        return
    
    if action_type == 'comment' and is_accepted:
        # Auto-whitelist for accepted comments
        max_accepted, time_window = rate_limiter.parse_rate_limit(config["auto_whitelist_comments_accepted"])
        if check_ip_activity(ip, 'comment_accepted', max_accepted, time_window):
            add_to_whitelist(ip, f"Auto-whitelisted: {max_accepted} comments accepted in {time_window}s")
            socketio.emit('ip_auto_whitelisted', {
                'ip': ip,
                'reason': f"Auto-whitelisted: {max_accepted} comments accepted in {time_window}s",
                'timestamp': datetime.now().isoformat()
            }, room='admin')
    elif action_type == 'question' and is_accepted:
        # Auto-whitelist for answered questions
        max_answered, time_window = rate_limiter.parse_rate_limit(config["auto_whitelist_questions_answered"])
        if check_ip_activity(ip, 'question_answered', max_answered, time_window):
            add_to_whitelist(ip, f"Auto-whitelisted: {max_answered} questions answered in {time_window}s")
            socketio.emit('ip_auto_whitelisted', {
                'ip': ip,
                'reason': f"Auto-whitelisted: {max_answered} questions answered in {time_window}s",
                'timestamp': datetime.now().isoformat()
            }, room='admin')
    elif action_type == 'comment' and not is_accepted:
        # Auto-blacklist for rejected comments
        max_rejected, time_window = rate_limiter.parse_rate_limit(config["auto_blacklist_comments_rejected"])
        if check_ip_activity(ip, 'comment_rejected', max_rejected, time_window):
            add_to_blacklist(ip, f"Auto-blacklisted: {max_rejected} comments rejected in {time_window}s")
            socketio.emit('ip_auto_blacklisted', {
                'ip': ip,
                'reason': f"Auto-blacklisted: {max_rejected} comments rejected in {time_window}s",
                'timestamp': datetime.now().isoformat()
            }, room='admin')
    elif action_type == 'question' and not is_accepted:
        # Auto-blacklist for rejected questions
        max_rejected, time_window = rate_limiter.parse_rate_limit(config["auto_blacklist_questions_rejected"])
        if check_ip_activity(ip, 'question_rejected', max_rejected, time_window):
            add_to_blacklist(ip, f"Auto-blacklisted: {max_rejected} questions rejected in {time_window}s")
            socketio.emit('ip_auto_blacklisted', {
                'ip': ip,
                'reason': f"Auto-blacklisted: {max_rejected} questions rejected in {time_window}s",
                'timestamp': datetime.now().isoformat()
            }, room='admin')

def check_ip_activity(ip, activity_type, max_count, time_window):
    """Check if IP has reached the threshold for auto-ACL"""
    try:
        with open(f'data/ip_activity_{activity_type}.json', 'r') as f:
            activities = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        activities = []
    
    now = time.time()
    cutoff_time = now - time_window
    
    # Filter activities for this IP within the time window
    ip_activities = [a for a in activities if a['ip'] == ip and a['timestamp'] > cutoff_time]
    
    # Add current activity
    ip_activities.append({
        'ip': ip,
        'timestamp': now,
        'type': activity_type
    })
    
    # Save updated activities
    activities = [a for a in activities if a['ip'] != ip or a['timestamp'] <= cutoff_time]
    activities.extend(ip_activities)
    
    with open(f'data/ip_activity_{activity_type}.json', 'w') as f:
        json.dump(activities, f, indent=2)
    
    return len(ip_activities) >= max_count

def load_json_file(filepath):
    """Load JSON data from file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_json_file(filepath, data):
    """Save JSON data to file"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

# Giveaway helper functions
def load_giveaways():
    """Load giveaways from file"""
    try:
        with open('data/giveaways.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_giveaways():
    """Save giveaways to file"""
    # Create a clean version without Timer objects for JSON serialization
    clean_giveaways = []
    for giveaway in giveaways:
        clean_giveaway = {
            'id': giveaway['id'],
            'name': giveaway['name'],
            'items': giveaway['items'],
            'recurring': giveaway['recurring'],
            'recurring_interval': giveaway['recurring_interval'],
            'remove_on_accept': giveaway['remove_on_accept'],
            'created_at': giveaway['created_at'],
            'status': giveaway['status']
        }
        clean_giveaways.append(clean_giveaway)
    
    with open('data/giveaways.json', 'w') as f:
        json.dump(clean_giveaways, f, indent=2)

def get_giveaway_config():
    """Get giveaway configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        return {
            'max_prize_per_ip': config.get('give_away_max_prize_per_ip', '2:64800'),
            'item_timeout': int(config.get('give_away_item_timeout', '30')),
            'max_payitforwards': int(config.get('give_away_max_payitforwards', '3'))
        }
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            'max_prize_per_ip': '2:64800',
            'item_timeout': 30,
            'max_payitforwards': 3
        }

def can_user_win_giveaway(ip):
    """Check if user can win a giveaway based on IP limits"""
    config = get_giveaway_config()
    max_prizes, time_window = config['max_prize_per_ip'].split(':')
    max_prizes = int(max_prizes)
    time_window = int(time_window)
    
    now = time.time()
    cutoff_time = now - time_window
    
    # Count prizes won in the time window
    if ip not in giveaway_winners:
        return True
    
    recent_wins = [win for win in giveaway_winners[ip] if win['timestamp'] > cutoff_time]
    return len(recent_wins) < max_prizes

def select_giveaway_winner():
    """Select a random winner from connected clients (excluding admins)"""
    # Filter out admin clients from eligible clients
    non_admin_clients = [client for client in connected_clients if client not in admin_connected_clients]
    eligible_clients = [client for client in non_admin_clients if can_user_win_giveaway(client)]
    
    # Debug info for admins
    debug_info = {
        'total_connected': len(connected_clients),
        'admin_connected': len(admin_connected_clients),
        'non_admin_clients': len(non_admin_clients),
        'eligible_clients': len(eligible_clients),
        'connected_ips': list(connected_clients),
        'admin_connected_ips': list(admin_connected_clients),
        'eligible_ips': eligible_clients
    }
    
    # Debug logging
    print(f"🎁 Giveaway Debug: {debug_info['total_connected']} connected, {debug_info['admin_connected']} admin, {debug_info['non_admin_clients']} non-admin, {debug_info['eligible_clients']} eligible")
    print(f"   Connected IPs: {debug_info['connected_ips']}")
    print(f"   Admin Connected IPs: {debug_info['admin_connected_ips']}")
    print(f"   Eligible IPs: {debug_info['eligible_ips']}")
    
    # Notify admins with debug info
    socketio.emit('admin_action_notification', {
        'action': 'giveaway_debug_info',
        'message': f"🔍 Giveaway Debug: {debug_info['total_connected']} connected clients, {debug_info['admin_connected']} admin, {debug_info['non_admin_clients']} non-admin, {debug_info['eligible_clients']} eligible",
        'timestamp': datetime.now().isoformat()
    })
    
    if not eligible_clients:
        return None
    return random.choice(eligible_clients)

def start_giveaway_timer(giveaway_id, delay_seconds):
    """Start a timer for a giveaway"""
    def timer_callback():
        execute_giveaway(giveaway_id)
    
    timer = threading.Timer(delay_seconds, timer_callback)
    timer.start()
    giveaway_timers[giveaway_id] = timer

def execute_giveaway(giveaway_id):
    """Execute a giveaway - select winner and notify clients"""
    giveaway = next((g for g in active_giveaways if g['id'] == giveaway_id), None)
    if not giveaway or not giveaway['items']:
        return
    
    # Notify admins that giveaway is about to happen
    socketio.emit('admin_action_notification', {
        'action': 'giveaway_executing',
        'message': f"🎁 Executing giveaway: {giveaway['name']} - Selecting winner from {len(giveaway['items'])} items",
        'timestamp': datetime.now().isoformat()
    }, room='admin')
    
    # Select a random item from the giveaway
    item = random.choice(giveaway['items'])
    
    # Select a winner
    winner_ip = select_giveaway_winner()
    if not winner_ip:
        # No eligible winners, pause giveaway and announce to everyone
        socketio.emit('admin_action_notification', {
            'action': 'giveaway_no_winner',
            'message': f"❌ No eligible winners found for giveaway: {giveaway['name']} - Pausing giveaway",
            'timestamp': datetime.now().isoformat()
        })
        
        # Pause the giveaway
        giveaway['status'] = 'paused'
        if giveaway in active_giveaways:
            active_giveaways.remove(giveaway)
        
        # Cancel any active timers
        if 'timeouts' in giveaway:
            for item_id, timeout_info in giveaway['timeouts'].items():
                if 'timer' in timeout_info:
                    timeout_info['timer'].cancel()
        
        # Cancel recurring timer if exists
        if 'recurring_timer' in giveaway:
            giveaway['recurring_timer'].cancel()
            del giveaway['recurring_timer']
        
        save_giveaways()
        
        socketio.emit('giveaway_paused', {
            'giveaway_id': giveaway_id,
            'giveaway_name': giveaway['name'],
            'reason': 'no_eligible_winners'
        })
        return
    
    # Record the winner
    if winner_ip not in giveaway_winners:
        giveaway_winners[winner_ip] = []
    
    giveaway_winners[winner_ip].append({
        'giveaway_id': giveaway_id,
        'item_id': item['id'],
        'timestamp': time.time()
    })
    
    # Notify all clients about winner selection
    socketio.emit('admin_action_notification', {
        'action': 'giveaway_winner_selected',
        'message': f"🎉 Winner selected for '{giveaway['name']}': {winner_ip} won '{item['name']}' - Awaiting accept/pay-it-forward ({get_giveaway_config()['item_timeout']}s timeout)",
        'timestamp': datetime.now().isoformat()
    })
    
    # Notify all clients about the winner selection
    socketio.emit('giveaway_winner_selected', {
        'giveaway_id': giveaway_id,
        'giveaway_name': giveaway['name'],
        'item': item,
        'timeout': get_giveaway_config()['item_timeout'],
        'winner_ip': winner_ip,
        'is_winner': False  # Will be set to true for the actual winner in frontend
    })
    
    # Also notify the specific winner with additional info
    socketio.emit('giveaway_winner_selected', {
        'giveaway_id': giveaway_id,
        'giveaway_name': giveaway['name'],
        'item': item,
        'timeout': get_giveaway_config()['item_timeout'],
        'winner_ip': winner_ip,
        'is_winner': True  # This is the actual winner
    }, room=winner_ip)
    
    # Start timeout timer for the item
    def timeout_callback():
        handle_giveaway_timeout(giveaway_id, item['id'], winner_ip)
    
    timeout_timer = threading.Timer(get_giveaway_config()['item_timeout'], timeout_callback)
    timeout_timer.start()
    
    # Store timeout info
    if 'timeouts' not in giveaway:
        giveaway['timeouts'] = {}
    giveaway['timeouts'][item['id']] = {
        'timer': timeout_timer,
        'winner_ip': winner_ip,
        'payitforwards': 0
    }
    
    # Schedule next giveaway if recurring
    if giveaway.get('recurring', False) and giveaway.get('recurring_interval', 0) > 0:
        def schedule_next():
            if giveaway in active_giveaways:  # Check if still active
                execute_giveaway(giveaway_id)
        
        next_interval = giveaway['recurring_interval'] * 60  # Convert to seconds
        next_timer = threading.Timer(next_interval, schedule_next)
        next_timer.start()
        
        # Store the recurring timer
        if 'recurring_timer' not in giveaway:
            giveaway['recurring_timer'] = next_timer
        
        # Notify all users about recurring schedule
        socketio.emit('admin_action_notification', {
            'action': 'giveaway_recurring_scheduled',
            'message': f"⏰ Recurring giveaway '{giveaway['name']}' scheduled for next execution in {giveaway['recurring_interval']} minutes",
            'timestamp': datetime.now().isoformat()
        })

def handle_giveaway_timeout(giveaway_id, item_id, winner_ip):
    """Handle giveaway item timeout - pay it forward or remove item"""
    giveaway = next((g for g in active_giveaways if g['id'] == giveaway_id), None)
    if not giveaway:
        return
    
    timeout_info = giveaway['timeouts'].get(item_id)
    if not timeout_info:
        return
    
    payitforwards = timeout_info['payitforwards']
    max_payitforwards = get_giveaway_config()['max_payitforwards']
    
    if payitforwards >= max_payitforwards:
        # Max payitforwards reached, remove item
        giveaway['items'] = [item for item in giveaway['items'] if item['id'] != item_id]
        
        # Notify all users about item removal
        socketio.emit('admin_action_notification', {
            'action': 'giveaway_item_removed',
            'message': f"🗑️ Item removed from '{giveaway['name']}' - Max pay-it-forwards reached ({max_payitforwards})",
            'timestamp': datetime.now().isoformat()
        })
        
        # Notify all clients
        socketio.emit('giveaway_item_removed', {
            'giveaway_id': giveaway_id,
            'giveaway_name': giveaway['name'],
            'reason': 'max_payitforwards_reached'
        })
        
        # Check if giveaway should be removed
        if not giveaway['items'] and not giveaway.get('recurring', False):
            active_giveaways.remove(giveaway)
            
            # Notify all users about giveaway ending
            socketio.emit('admin_action_notification', {
                'action': 'giveaway_ended',
                'message': f"🏁 Giveaway '{giveaway['name']}' has ended - All items have been distributed or removed",
                'timestamp': datetime.now().isoformat()
            })
            
            socketio.emit('giveaway_ended', {
                'giveaway_id': giveaway_id,
                'giveaway_name': giveaway['name']
            })
    else:
        # Pay it forward
        pay_it_forward(giveaway_id, item_id, winner_ip)

def pay_it_forward(giveaway_id, item_id, previous_winner_ip):
    """Pay it forward to another winner"""
    giveaway = next((g for g in active_giveaways if g['id'] == giveaway_id), None)
    if not giveaway:
        return
    
    # Notify all clients about pay it forward
    socketio.emit('giveaway_pay_it_forward', {
        'giveaway_id': giveaway_id,
        'giveaway_name': giveaway['name']
    })
    
    # Notify all clients about automatic pay it forward
    socketio.emit('admin_action_notification', {
        'action': 'giveaway_payitforward_auto',
        'message': f"⏰ Pay-it-forward triggered for '{giveaway['name']}' - Previous winner didn't respond in time, selecting new winner",
        'timestamp': datetime.now().isoformat()
    })
    
    # Select new winner
    new_winner_ip = select_giveaway_winner()
    if not new_winner_ip:
        # No eligible winners, pause giveaway and announce to everyone
        socketio.emit('admin_action_notification', {
            'action': 'giveaway_no_winner_payitforward',
            'message': f"❌ No eligible winners found for pay-it-forward in '{giveaway['name']}' - Pausing giveaway",
            'timestamp': datetime.now().isoformat()
        })
        
        # Pause the giveaway
        giveaway['status'] = 'paused'
        if giveaway in active_giveaways:
            active_giveaways.remove(giveaway)
        
        # Cancel any active timers
        if 'timeouts' in giveaway:
            for item_id, timeout_info in giveaway['timeouts'].items():
                if 'timer' in timeout_info:
                    timeout_info['timer'].cancel()
        
        # Cancel recurring timer if exists
        if 'recurring_timer' in giveaway:
            giveaway['recurring_timer'].cancel()
            del giveaway['recurring_timer']
        
        save_giveaways()
        
        socketio.emit('giveaway_paused', {
            'giveaway_id': giveaway_id,
            'giveaway_name': giveaway['name'],
            'reason': 'no_eligible_winners_payitforward'
        })
        return
    
    # Record the new winner
    if new_winner_ip not in giveaway_winners:
        giveaway_winners[new_winner_ip] = []
    
    giveaway_winners[new_winner_ip].append({
        'giveaway_id': giveaway_id,
        'item_id': item_id,
        'timestamp': time.time()
    })
    
    # Update payitforward count
    if 'timeouts' in giveaway and item_id in giveaway['timeouts']:
        giveaway['timeouts'][item_id]['payitforwards'] += 1
    
    # Notify the new winner
    item = next((item for item in giveaway['items'] if item['id'] == item_id), None)
    if item:
        # Notify all clients about new winner selection
        socketio.emit('admin_action_notification', {
            'action': 'giveaway_new_winner_payitforward',
            'message': f"🎉 New winner selected for pay-it-forward in '{giveaway['name']}': {new_winner_ip} won '{item['name']}' - Awaiting accept/pay-it-forward ({get_giveaway_config()['item_timeout']}s timeout)",
            'timestamp': datetime.now().isoformat()
        })
        
        # Notify all clients about the new winner selection
        socketio.emit('giveaway_winner_selected', {
            'giveaway_id': giveaway_id,
            'giveaway_name': giveaway['name'],
            'item': item,
            'timeout': get_giveaway_config()['item_timeout'],
            'winner_ip': new_winner_ip,
            'is_winner': False  # Will be set to true for the actual winner in frontend
        })
        
        # Also notify the specific winner with additional info
        socketio.emit('giveaway_winner_selected', {
            'giveaway_id': giveaway_id,
            'giveaway_name': giveaway['name'],
            'item': item,
            'timeout': get_giveaway_config()['item_timeout'],
            'winner_ip': new_winner_ip,
            'is_winner': True  # This is the actual winner
        }, room=new_winner_ip)
        
        # Start new timeout timer
        def timeout_callback():
            handle_giveaway_timeout(giveaway_id, item_id, new_winner_ip)
        
        timeout_timer = threading.Timer(get_giveaway_config()['item_timeout'], timeout_callback)
        timeout_timer.start()
        
        giveaway['timeouts'][item_id] = {
            'timer': timeout_timer,
            'winner_ip': new_winner_ip,
            'payitforwards': giveaway['timeouts'][item_id]['payitforwards']
        }

@app.route('/')
def index():
    """Serve the main page"""
    # Load config to get app_name
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        app_name = config.get('app_name', 'pysembly')
    except (FileNotFoundError, json.JSONDecodeError):
        app_name = 'pysembly'
    
    # Get client IP instead of server IP
    client_ip = get_client_ip()
    
    return render_template('index.html', 
                         app_name=app_name, 
                         server_ip=client_ip,
                         current_question=current_question,
                         current_comment=current_comment)

@app.route('/api/config')
def get_config():
    """Get application configuration"""
    # Read from main config.json
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        return jsonify(config)
    except FileNotFoundError:
        return jsonify({"app_name": "pysembly"})

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """Get all questions"""
    questions = load_json_file('data/questions.json')
    return jsonify(questions)

@app.route('/api/questions', methods=['POST'])
def add_question():
    """Add a new question"""
    client_ip = get_client_ip()
    
    # Check rate limiting
    allowed, error_msg = rate_limiter.check_rate_limit(client_ip)
    if not allowed:
        # Emit rate limit notification to admins
        socketio.emit('rate_limit_hit', {
            'ip': client_ip,
            'message': error_msg,
            'timestamp': datetime.now().isoformat(),
            'type': 'question'
        }, room='admin')
        
        # Also emit to Live Feed for all admins (only if not blacklisted)
        if not rate_limiter.is_ip_blacklisted(client_ip):
            socketio.emit('admin_action_notification', {
                'action': 'rate_limit_hit',
                'message': f'Rate limit hit from {client_ip}: {error_msg}',
                'timestamp': datetime.now().isoformat()
            }, room='admin')
        
        return jsonify({'error': error_msg}), 429
    
    data = request.get_json()
    question_text = data.get('question', '').strip()
    
    if not question_text:
        return jsonify({'error': 'Question cannot be empty'}), 400
    
    question = {
        'id': str(uuid.uuid4()),
        'text': question_text,
        'timestamp': datetime.now().isoformat(),
        'status': 'pending',
        'ip': client_ip
    }
    
    questions = load_json_file('data/questions.json')
    questions.append(question)
    save_json_file('data/questions.json', questions)
    
    # Emit to all clients
    socketio.emit('new_question', question)
    
    return jsonify(question)

@app.route('/api/questions/<question_id>', methods=['DELETE'])
def delete_question(question_id):
    """Delete a question"""
    global current_question
    
    # Check if this is the current question
    if current_question and current_question['id'] == question_id:
        current_question = None
        # Emit specific event for current question deletion
        socketio.emit('current_question_deleted', {'id': question_id})
    else:
        # Remove from pending questions
        questions = load_json_file('data/questions.json')
        questions = [q for q in questions if q['id'] != question_id]
        save_json_file('data/questions.json', questions)
    
    # Emit general question deleted event
    socketio.emit('question_deleted', {'id': question_id})
    return jsonify({'success': True})

@app.route('/api/questions/<question_id>/accept', methods=['POST'])
def accept_question(question_id):
    """Accept a question and display it"""
    global current_question
    
    questions = load_json_file('data/questions.json')
    question = next((q for q in questions if q['id'] == question_id), None)
    
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    
    # Check auto-ACL for question acceptance
    if 'ip' in question:
        check_auto_acl(question['ip'], 'question', True)
    
    # Remove from pending questions
    questions = [q for q in questions if q['id'] != question_id]
    save_json_file('data/questions.json', questions)
    
    current_question = question
    socketio.emit('question_accepted', question)
    socketio.emit('question_removed_from_list', {'id': question_id})
    
    return jsonify(question)

@app.route('/api/questions/<question_id>/answer', methods=['POST'])
def answer_question(question_id):
    """Mark question as answered"""
    global current_question
    
    # Check if this is the current question
    if current_question and current_question['id'] == question_id:
        question = current_question
    else:
        # Fallback: look in pending questions
        questions = load_json_file('data/questions.json')
        question = next((q for q in questions if q['id'] == question_id), None)
    
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    
    # Check auto-ACL for question answering
    if 'ip' in question:
        check_auto_acl(question['ip'], 'question', True)
    
    # Move to answered questions
    answered_questions = load_json_file('data/questions_answered.json')
    question['answered_at'] = datetime.now().isoformat()
    answered_questions.append(question)
    save_json_file('data/questions_answered.json', answered_questions)
    
    # Remove from pending questions if it exists there
    questions = load_json_file('data/questions.json')
    questions = [q for q in questions if q['id'] != question_id]
    save_json_file('data/questions.json', questions)
    
    current_question = None
    socketio.emit('question_answered', {'id': question_id})
    
    # Emit updated answered questions to all clients
    answered_questions = load_json_file('data/questions_answered.json')
    socketio.emit('answered_questions_updated', answered_questions)
    
    return jsonify({'success': True})

@app.route('/api/questions/<question_id>/reject', methods=['POST'])
def reject_question(question_id):
    """Reject a question (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    questions = load_json_file('data/questions.json')
    question = next((q for q in questions if q['id'] == question_id), None)
    
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    
    # Check auto-ACL for question rejection
    if 'ip' in question:
        check_auto_acl(question['ip'], 'question', False)
    
    # Remove from pending questions
    questions = [q for q in questions if q['id'] != question_id]
    save_json_file('data/questions.json', questions)
    
    socketio.emit('question_rejected', {'id': question_id}, room='admin')
    return jsonify({'success': True})

@app.route('/api/comments/<comment_id>/reject', methods=['POST'])
def reject_comment(comment_id):
    """Reject a comment (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    # Find the comment in pending comments
    comment = next((c for c in pending_comments if c['id'] == comment_id), None)
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404
    
    # Check auto-ACL for comment rejection
    if 'ip' in comment:
        check_auto_acl(comment['ip'], 'comment', False)
    
    # Remove from pending comments
    pending_comments.remove(comment)
    
    socketio.emit('comment_rejected', {'id': comment_id}, room='admin')
    return jsonify({'success': True})

@app.route('/api/comments', methods=['POST'])
def add_comment():
    """Add a new comment"""
    client_ip = get_client_ip()
    
    # Check rate limiting
    allowed, error_msg = rate_limiter.check_rate_limit(client_ip)
    if not allowed:
        # Emit rate limit notification to admins
        socketio.emit('rate_limit_hit', {
            'ip': client_ip,
            'message': error_msg,
            'timestamp': datetime.now().isoformat(),
            'type': 'comment'
        }, room='admin')
        
        # Also emit to Live Feed for all admins (only if not blacklisted)
        if not rate_limiter.is_ip_blacklisted(client_ip):
            socketio.emit('admin_action_notification', {
                'action': 'rate_limit_hit',
                'message': f'Rate limit hit from {client_ip}: {error_msg}',
                'timestamp': datetime.now().isoformat()
            }, room='admin')
        
        return jsonify({'error': error_msg}), 429
    
    data = request.get_json()
    comment_text = data.get('comment', '').strip()
    
    if not comment_text:
        return jsonify({'error': 'Comment cannot be empty'}), 400
    
    comment = {
        'id': str(uuid.uuid4()),
        'text': comment_text,
        'timestamp': datetime.now().isoformat(),
        'status': 'pending',
        'ip': client_ip
    }
    
    pending_comments.append(comment)
    socketio.emit('new_comment', comment)
    return jsonify(comment)

@app.route('/api/comments/<comment_id>/accept', methods=['POST'])
def accept_comment(comment_id):
    """Accept a comment and display it"""
    global current_comment
    
    # Find the comment in pending comments
    comment = next((c for c in pending_comments if c['id'] == comment_id), None)
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404
    
    # Check auto-ACL for comment acceptance
    if 'ip' in comment:
        check_auto_acl(comment['ip'], 'comment', True)
    
    # Remove from pending comments
    pending_comments.remove(comment)
    
    current_comment = comment
    socketio.emit('comment_accepted', comment)
    socketio.emit('comment_removed_from_list', {'id': comment_id})
    
    return jsonify(comment)

@app.route('/api/comments/<comment_id>/answer', methods=['POST'])
def answer_comment(comment_id):
    """Mark comment as accepted"""
    global current_comment
    
    # Check if this is the current comment
    if current_comment and current_comment['id'] == comment_id:
        comment = current_comment
    else:
        # Fallback: look in pending comments
        comment = next((c for c in pending_comments if c['id'] == comment_id), None)
        if comment:
            pending_comments.remove(comment)
    
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404
    
    # Move to accepted comments
    accepted_comments = load_json_file('data/comments_accepted.json')
    comment['accepted_at'] = datetime.now().isoformat()
    accepted_comments.append(comment)
    save_json_file('data/comments_accepted.json', accepted_comments)
    
    current_comment = None
    socketio.emit('comment_answered', {'id': comment_id})
    
    # Emit updated answered comments to all clients
    answered_comments = load_json_file('data/comments_accepted.json')
    socketio.emit('answered_comments_updated', answered_comments)
    
    return jsonify({'success': True})

@app.route('/api/statistics')
def get_statistics():
    """Get application statistics"""
    questions = load_json_file('data/questions.json')
    answered_questions = load_json_file('data/questions_answered.json')
    accepted_comments = load_json_file('data/comments_accepted.json')
    
    return jsonify({
        'questions_asked': len(questions),
        'questions_answered': len(answered_questions),
        'comments_given': len(pending_comments),
        'comments_accepted': len(accepted_comments)
    })

@app.route('/api/topics', methods=['GET'])
def get_topics():
    """Get all topics"""
    topics = load_json_file('data/topics.json')
    return jsonify(topics)

@app.route('/api/topics', methods=['POST'])
def add_topic():
    """Add a new topic"""
    data = request.get_json()
    topic_text = data.get('topic', '').strip()
    
    if not topic_text:
        return jsonify({'error': 'Topic cannot be empty'}), 400
    
    topic = {
        'id': str(uuid.uuid4()),
        'text': topic_text,
        'timestamp': datetime.now().isoformat()
    }
    
    topics = load_json_file('data/topics.json')
    topics.append(topic)
    save_json_file('data/topics.json', topics)
    
    socketio.emit('topic_added', topic)
    
    # Announce to all clients that a topic has been added
    socketio.emit('admin_action_notification', {
        'action': 'topic_added',
        'message': f'New topic added: {topic_text}',
        'timestamp': datetime.now().isoformat()
    })
    
    return jsonify(topic)

@app.route('/api/topics/<topic_id>', methods=['DELETE'])
def delete_topic(topic_id):
    """Delete a topic"""
    topics = load_json_file('data/topics.json')
    topic = next((t for t in topics if t['id'] == topic_id), None)
    topics = [t for t in topics if t['id'] != topic_id]
    save_json_file('data/topics.json', topics)
    
    socketio.emit('topic_deleted', {'id': topic_id})
    
    # Announce to all clients that a topic has been removed
    if topic:
        socketio.emit('admin_action_notification', {
            'action': 'topic_removed',
            'message': f'Topic removed: {topic.get("text", "Unknown topic")}',
            'timestamp': datetime.now().isoformat()
        })
    
    return jsonify({'success': True})

@app.route('/api/admin/reset', methods=['POST'])
def reset_all_data():
    """Reset all data (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    # Clear all JSON files
    save_json_file('data/questions.json', [])
    save_json_file('data/questions_answered.json', [])
    save_json_file('data/comments_accepted.json', [])
    save_json_file('data/topics.json', [])
    
    # Clear global state
    global current_question, current_comment, pending_comments
    current_question = None
    current_comment = None
    pending_comments = []
    
    # Emit specific events to clear client-side lists
    socketio.emit('data_reset', {})
    socketio.emit('answered_questions_updated', [])
    socketio.emit('answered_comments_updated', [])
    socketio.emit('question_removed_from_list', {'clear_all': True})
    socketio.emit('comment_removed_from_list', {'clear_all': True})
    
    # Notify all admins about the reset
    socketio.emit('admin_action_notification', {
        'action': 'data_reset',
        'message': 'All data has been reset',
        'timestamp': datetime.now().isoformat()
    }, room='admin')
    
    return jsonify({'success': True})

@app.route('/api/comments', methods=['GET'])
def get_comments():
    """Get all pending comments"""
    return jsonify(pending_comments)

@app.route('/api/questions_answered', methods=['GET'])
def get_answered_questions():
    """Get all answered questions"""
    answered_questions = load_json_file('data/questions_answered.json')
    return jsonify(answered_questions)

@app.route('/api/comments_answered', methods=['GET'])
def get_answered_comments():
    """Get all answered comments"""
    answered_comments = load_json_file('data/comments_accepted.json')
    return jsonify(answered_comments)

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login with configurable password"""
    client_ip = get_client_ip()
    data = request.get_json()
    password = data.get('password', '')
    
    # Load config to get admin password
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        admin_password = config.get('admin_password', 'admin')
    except (FileNotFoundError, json.JSONDecodeError):
        admin_password = 'admin'  # fallback to default
    
    if password == admin_password:
        session_id = str(uuid.uuid4())
        admin_sessions.add(session_id)
        
        # Create a unique browser identifier
        user_agent = request.headers.get('User-Agent', '')
        browser_id = f"{client_ip}_{user_agent}"
        browser_admin_sessions[browser_id] = session_id
        
        # Store in Flask session for compatibility
        session['admin_session'] = session_id
        
        # Debug logging
        print(f"🔐 Admin login: Session {session_id} created for browser {browser_id}")
        print(f"   Current admin_sessions: {len(admin_sessions)}")
        print(f"   Browser admin sessions: {len(browser_admin_sessions)}")
        
        # Emit admin login event to all clients
        socketio.emit('admin_logged_in', {'session_id': session_id})
        
        return jsonify({'success': True, 'session_id': session_id})
    
    return jsonify({'error': 'Invalid password'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout"""
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')
    browser_id = f"{client_ip}_{user_agent}"
    
    # Remove from browser admin sessions
    if browser_id in browser_admin_sessions:
        session_id = browser_admin_sessions[browser_id]
        del browser_admin_sessions[browser_id]
        
        # Also remove from global admin sessions
        if session_id in admin_sessions:
            admin_sessions.remove(session_id)
        
        print(f"🔐 Admin logout: Session {session_id} removed for browser {browser_id}")
        print(f"   Current admin_sessions: {len(admin_sessions)}")
        print(f"   Browser admin sessions: {len(browser_admin_sessions)}")
    
    session.pop('admin_session', None)
    return jsonify({'success': True})

@app.route('/api/admin/status', methods=['GET'])
def check_admin_status():
    """Check if current session is admin"""
    is_admin_status = is_admin()
    return jsonify({'is_admin': is_admin_status})

@app.route('/api/admin/video-source', methods=['POST'])
def change_video_source():
    """Change video source (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    data = request.get_json()
    video_url = data.get('url', '').strip()
    original_url = data.get('original_url', '').strip()
    
    if not video_url:
        return jsonify({'error': 'Video URL is required'}), 400
    
    global current_video_source
    current_video_source = video_url
    
    # Emit to all clients
    socketio.emit('video_source_changed', {
        'url': video_url,
        'original_url': original_url
    })
    
    # Notify all admins about the video source change
    socketio.emit('admin_action_notification', {
        'action': 'video_source_changed',
        'message': f'Video source changed to: {video_url}',
        'timestamp': datetime.now().isoformat()
    }, room='admin')
    
    return jsonify({'success': True})

@app.route('/api/admin/config', methods=['GET'])
def get_admin_config():
    """Get admin configuration (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        return jsonify(config)
    except FileNotFoundError:
        return jsonify({'error': 'Config file not found'}), 404

@app.route('/api/admin/config', methods=['POST'])
def update_admin_config():
    """Update admin configuration (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    data = request.get_json()
    
    try:
        with open('config.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        # Reload rate limiter config
        rate_limiter.config = data
        
        # Notify all admins about the config change
        socketio.emit('admin_action_notification', {
            'action': 'config_updated',
            'message': 'Configuration has been updated',
            'timestamp': datetime.now().isoformat()
        }, room='admin')
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/whitelist', methods=['GET'])
def get_whitelist():
    """Get whitelist (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    try:
        with open('access/white_list.json', 'r') as f:
            whitelist = json.load(f)
        return jsonify(whitelist)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify([])

@app.route('/api/admin/blacklist', methods=['GET'])
def get_blacklist():
    """Get blacklist (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    try:
        with open('access/black_list.json', 'r') as f:
            blacklist = json.load(f)
        return jsonify(blacklist)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify([])

@app.route('/api/admin/whitelist', methods=['POST'])
def add_to_whitelist_api():
    """Add IP to whitelist (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    data = request.get_json()
    ip = data.get('ip', '').strip()
    reason = data.get('reason', '')
    
    if not ip:
        return jsonify({'error': 'IP address is required'}), 400
    
    success = add_to_whitelist(ip, reason)
    if success:
        # Notify all admins about the whitelist addition
        socketio.emit('admin_action_notification', {
            'action': 'ip_whitelisted',
            'message': f'IP {ip} added to whitelist: {reason}',
            'timestamp': datetime.now().isoformat()
        }, room='admin')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'IP already in whitelist'}), 400

@app.route('/api/admin/blacklist', methods=['POST'])
def add_to_blacklist_api():
    """Add IP to blacklist (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    data = request.get_json()
    ip = data.get('ip', '').strip()
    reason = data.get('reason', '')
    
    if not ip:
        return jsonify({'error': 'IP address is required'}), 400
    
    success = add_to_blacklist(ip, reason)
    if success:
        # Notify all admins about the blacklist addition
        socketio.emit('admin_action_notification', {
            'action': 'ip_blacklisted',
            'message': f'IP {ip} added to blacklist: {reason}',
            'timestamp': datetime.now().isoformat()
        }, room='admin')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'IP already in blacklist'}), 400

@app.route('/api/admin/whitelist/<ip>', methods=['DELETE'])
def remove_from_whitelist(ip):
    """Remove IP from whitelist (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    try:
        with open('access/white_list.json', 'r') as f:
            whitelist = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'error': 'Whitelist not found'}), 404
    
    # Remove IP from whitelist
    whitelist = [entry for entry in whitelist if entry.get('ip') != ip]
    
    with open('access/white_list.json', 'w') as f:
        json.dump(whitelist, f, indent=2)
    
    # Notify all admins about the whitelist removal
    socketio.emit('admin_action_notification', {
        'action': 'ip_removed_from_whitelist',
        'message': f'IP {ip} removed from whitelist',
        'timestamp': datetime.now().isoformat()
    }, room='admin')
    
    return jsonify({'success': True})

@app.route('/api/admin/blacklist/<ip>', methods=['DELETE'])
def remove_from_blacklist(ip):
    """Remove IP from blacklist (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    try:
        with open('access/black_list.json', 'r') as f:
            blacklist = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'error': 'Blacklist not found'}), 404
    
    # Remove IP from blacklist
    blacklist = [entry for entry in blacklist if entry.get('ip') != ip]
    
    with open('access/black_list.json', 'w') as f:
        json.dump(blacklist, f, indent=2)
    
    # Notify all admins about the blacklist removal
    socketio.emit('admin_action_notification', {
        'action': 'ip_removed_from_blacklist',
        'message': f'IP {ip} removed from blacklist',
        'timestamp': datetime.now().isoformat()
    }, room='admin')
    
    return jsonify({'success': True})

# Giveaway API endpoints
@app.route('/api/giveaways', methods=['GET'])
def get_giveaways():
    """Get all giveaways"""
    # Create a clean version without Timer objects for JSON serialization
    clean_giveaways = []
    for giveaway in giveaways:
        clean_giveaway = {
            'id': giveaway['id'],
            'name': giveaway['name'],
            'items': giveaway['items'],
            'recurring': giveaway['recurring'],
            'recurring_interval': giveaway['recurring_interval'],
            'remove_on_accept': giveaway['remove_on_accept'],
            'created_at': giveaway['created_at'],
            'status': giveaway['status']
        }
        clean_giveaways.append(clean_giveaway)
    
    return jsonify(clean_giveaways)

@app.route('/api/giveaways', methods=['POST'])
def create_giveaway():
    """Create a new giveaway (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    data = request.get_json()
    name = data.get('name', '').strip()
    delay_minutes = data.get('delay_minutes', 0)
    recurring = data.get('recurring', False)
    recurring_interval = data.get('recurring_interval', 0)
    remove_on_accept = data.get('remove_on_accept', True)
    
    if not name:
        return jsonify({'error': 'Giveaway name is required'}), 400
    
    # Validate delay (must be less than 6 hours for non-recurring)
    if not recurring and delay_minutes > 360:
        return jsonify({'error': 'Delay must be less than 6 hours for non-recurring giveaways'}), 400
    
    giveaway = {
        'id': str(uuid.uuid4()),
        'name': name,
        'items': [],
        'recurring': recurring,
        'recurring_interval': recurring_interval,
        'remove_on_accept': remove_on_accept,
        'created_at': datetime.now().isoformat(),
        'status': 'pending'
    }
    
    giveaways.append(giveaway)
    save_giveaways()
    
    # Giveaways are created in 'pending' status and must be manually started
    # No automatic starting - admin must click start button
    
    socketio.emit('giveaway_created', giveaway, room='admin')
    return jsonify(giveaway)

@app.route('/api/giveaways/<giveaway_id>', methods=['DELETE'])
def delete_giveaway(giveaway_id):
    """Delete a giveaway (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    global giveaways, active_giveaways
    
    # Remove from giveaways list
    giveaway = next((g for g in giveaways if g['id'] == giveaway_id), None)
    if not giveaway:
        return jsonify({'error': 'Giveaway not found'}), 404
    
    # Calculate statistics before deletion
    total_items = len(giveaway['items'])
    payitforward_count = 0
    accepted_count = 0
    
    # Count pay-it-forwards from timeout info
    if 'timeouts' in giveaway:
        for item_id, timeout_info in giveaway['timeouts'].items():
            payitforward_count += timeout_info.get('payitforwards', 0)
    
    # Count accepted items (items that were won and accepted)
    # This is tricky because accepted items are removed from the items list
    # We need to track this differently - for now, we'll estimate based on payitforwards
    
    giveaways = [g for g in giveaways if g['id'] != giveaway_id]
    active_giveaways = [g for g in active_giveaways if g['id'] != giveaway_id]
    
    # Cancel timer if exists
    if giveaway_id in giveaway_timers:
        giveaway_timers[giveaway_id].cancel()
        del giveaway_timers[giveaway_id]
    
    # Cancel recurring timer if exists
    if 'recurring_timer' in giveaway:
        giveaway['recurring_timer'].cancel()
    
    # Cancel all timeout timers
    if 'timeouts' in giveaway:
        for item_id, timeout_info in giveaway['timeouts'].items():
            if 'timer' in timeout_info:
                timeout_info['timer'].cancel()
    
    save_giveaways()
    
    # Announce giveaway removal with statistics
    message = f"Giveaway '{giveaway['name']}' has been removed. "
    message += f"Items remaining: {total_items}"
    if payitforward_count > 0:
        message += f", Pay-it-forwards: {payitforward_count}"
    
    socketio.emit('admin_action_notification', {
        'action': 'giveaway_removed',
        'message': message,
        'timestamp': datetime.now().isoformat()
    })
    
    socketio.emit('giveaway_deleted', {'id': giveaway_id}, room='admin')
    return jsonify({'success': True})

@app.route('/api/giveaways/<giveaway_id>/items', methods=['POST'])
def add_giveaway_item(giveaway_id):
    """Add an item to a giveaway (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    data = request.get_json()
    item_name = data.get('name', '').strip()
    item_link = data.get('link', '').strip()
    
    if not item_name:
        return jsonify({'error': 'Item name is required'}), 400
    
    giveaway = next((g for g in giveaways if g['id'] == giveaway_id), None)
    if not giveaway:
        return jsonify({'error': 'Giveaway not found'}), 404
    
    item = {
        'id': str(uuid.uuid4()),
        'name': item_name,
        'link': item_link,
        'added_at': datetime.now().isoformat()
    }
    
    giveaway['items'].append(item)
    save_giveaways()
    
    socketio.emit('giveaway_item_added', {
        'giveaway_id': giveaway_id,
        'item': item
    }, room='admin')
    
    return jsonify(item)

@app.route('/api/giveaways/<giveaway_id>/items/<item_id>', methods=['DELETE'])
def delete_giveaway_item(giveaway_id, item_id):
    """Delete an item from a giveaway (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    giveaway = next((g for g in giveaways if g['id'] == giveaway_id), None)
    if not giveaway:
        return jsonify({'error': 'Giveaway not found'}), 404
    
    item = next((item for item in giveaway['items'] if item['id'] == item_id), None)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    giveaway['items'] = [item for item in giveaway['items'] if item['id'] != item_id]
    save_giveaways()
    
    socketio.emit('giveaway_item_deleted', {
        'giveaway_id': giveaway_id,
        'item_id': item_id
    }, room='admin')
    
    return jsonify({'success': True})

@app.route('/api/giveaways/<giveaway_id>/accept', methods=['POST'])
def accept_giveaway_item(giveaway_id):
    """Accept a giveaway item (winner only)"""
    client_ip = get_client_ip()
    
    # Find the giveaway and check if this IP is the winner
    giveaway = next((g for g in active_giveaways if g['id'] == giveaway_id), None)
    if not giveaway:
        return jsonify({'error': 'Giveaway not found'}), 404
    
    # Find the item that this IP won
    won_item = None
    for item in giveaway['items']:
        if 'timeouts' in giveaway and item['id'] in giveaway['timeouts']:
            if giveaway['timeouts'][item['id']]['winner_ip'] == client_ip:
                won_item = item
                break
    
    if not won_item:
        return jsonify({'error': 'You are not the winner of this giveaway'}), 403
    
    # Cancel timeout timer
    if 'timeouts' in giveaway and won_item['id'] in giveaway['timeouts']:
        giveaway['timeouts'][won_item['id']]['timer'].cancel()
        del giveaway['timeouts'][won_item['id']]
    
    # Remove item if configured to do so
    if giveaway.get('remove_on_accept', True):
        giveaway['items'] = [item for item in giveaway['items'] if item['id'] != won_item['id']]
        
        # Check if giveaway should be removed
        if not giveaway['items'] and not giveaway.get('recurring', False):
            active_giveaways.remove(giveaway)
            socketio.emit('giveaway_ended', {
                'giveaway_id': giveaway_id,
                'giveaway_name': giveaway['name']
            })
    
    # Notify all clients
    remaining_items = len(giveaway['items'])
    message = f"✅ Winner accepted item from '{giveaway['name']}': '{won_item['name']}'"
    
    if giveaway.get('recurring', False) and remaining_items > 0:
        message += f". This giveaway will happen again in {giveaway['recurring_interval']} minutes and has {remaining_items} more items left."
    elif remaining_items > 0:
        message += f". {remaining_items} items remaining in this giveaway."
    else:
        message += ". No more items remaining in this giveaway."
    
    socketio.emit('admin_action_notification', {
        'action': 'giveaway_accepted',
        'message': message,
        'timestamp': datetime.now().isoformat()
    })
    
    # Send item details to winner
    socketio.emit('giveaway_item_details', {
        'giveaway_id': giveaway_id,
        'giveaway_name': giveaway['name'],
        'item': won_item
    }, room=client_ip)
    
    return jsonify({'success': True, 'item': won_item})

@app.route('/api/giveaways/<giveaway_id>/payitforward', methods=['POST'])
def pay_it_forward_giveaway(giveaway_id):
    """Pay it forward for a giveaway item (winner only)"""
    client_ip = get_client_ip()
    
    # Find the giveaway and check if this IP is the winner
    giveaway = next((g for g in active_giveaways if g['id'] == giveaway_id), None)
    if not giveaway:
        return jsonify({'error': 'Giveaway not found'}), 404
    
    # Find the item that this IP won
    won_item = None
    for item in giveaway['items']:
        if 'timeouts' in giveaway and item['id'] in giveaway['timeouts']:
            if giveaway['timeouts'][item['id']]['winner_ip'] == client_ip:
                won_item = item
                break
    
    if not won_item:
        return jsonify({'error': 'You are not the winner of this giveaway'}), 403
    
    # Cancel current timeout timer
    if 'timeouts' in giveaway and won_item['id'] in giveaway['timeouts']:
        giveaway['timeouts'][won_item['id']]['timer'].cancel()
    
    # Pay it forward
    pay_it_forward(giveaway_id, won_item['id'], client_ip)
    
    # Notify all clients about manual pay-it-forward
    socketio.emit('admin_action_notification', {
        'action': 'giveaway_payitforward_manual',
        'message': f"🔄 Winner chose to Pay It Forward for '{giveaway['name']}' - '{won_item['name']}' will be given to another user",
        'timestamp': datetime.now().isoformat()
    })
    
    return jsonify({'success': True})

@app.route('/api/giveaways/<giveaway_id>/start', methods=['POST'])
def start_giveaway(giveaway_id):
    """Start a giveaway (admin only)"""
    # Debug admin status
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')
    browser_id = f"{client_ip}_{user_agent}"
    is_admin_status = is_admin()
    
    print(f"🔍 Start Giveaway Debug:")
    print(f"   Client IP: {client_ip}")
    print(f"   User-Agent: {user_agent[:50]}...")
    print(f"   Browser ID: {browser_id}")
    print(f"   Is Admin: {is_admin_status}")
    print(f"   Browser admin sessions: {list(browser_admin_sessions.keys())}")
    
    if not is_admin_status:
        return jsonify({'error': 'Not authorized'}), 401
    
    giveaway = next((g for g in giveaways if g['id'] == giveaway_id), None)
    if not giveaway:
        return jsonify({'error': 'Giveaway not found'}), 404
    
    # Check if already active (either in status or in active_giveaways list)
    if giveaway['status'] == 'active' and any(g['id'] == giveaway_id for g in active_giveaways):
        return jsonify({'error': 'Giveaway is already active'}), 400
    
    if not giveaway['items']:
        return jsonify({'error': 'Cannot start giveaway without items'}), 400
    
    # Check if this is a resume (was paused) or start (was stopped)
    was_paused = giveaway['status'] == 'paused'
    
    # Start or resume the giveaway
    giveaway['status'] = 'active'
    
    # Only add to active_giveaways if not already there
    if not any(g['id'] == giveaway_id for g in active_giveaways):
        active_giveaways.append(giveaway)
    
    save_giveaways()
    
    # Execute first giveaway immediately
    execute_giveaway(giveaway_id)
    
    # Determine if this is a start or resume
    action = 'resumed' if was_paused else 'started'
    action_emoji = '▶️' if action == 'resumed' else '🚀'
    
    socketio.emit('admin_action_notification', {
        'action': f'giveaway_{action}',
        'message': f"{action_emoji} Giveaway '{giveaway['name']}' {action} - {len(giveaway['items'])} items available",
        'timestamp': datetime.now().isoformat()
    })
    
    socketio.emit(f'giveaway_{action}', {
        'giveaway_id': giveaway_id,
        'giveaway_name': giveaway['name']
    })
    
    return jsonify({'success': True})

@app.route('/api/giveaways/<giveaway_id>/stop', methods=['POST'])
def stop_giveaway(giveaway_id):
    """Stop a giveaway (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    global active_giveaways
    
    # Find giveaway in either active_giveaways or main giveaways list
    giveaway = next((g for g in active_giveaways if g['id'] == giveaway_id), None)
    if not giveaway:
        giveaway = next((g for g in giveaways if g['id'] == giveaway_id), None)
    
    if not giveaway:
        return jsonify({'error': 'Giveaway not found'}), 404
    
    if giveaway['status'] not in ['active', 'paused']:
        return jsonify({'error': 'Giveaway is not active or paused'}), 400
    
    # Calculate statistics before stopping
    total_items = len(giveaway['items'])
    accepted_count = 0
    payitforward_count = 0
    
    # Count accepted items (items that were won and accepted)
    for item in giveaway['items']:
        if 'timeouts' in giveaway and item['id'] in giveaway['timeouts']:
            timeout_info = giveaway['timeouts'][item['id']]
            payitforward_count += timeout_info.get('payitforwards', 0)
            # If item was accepted, it would have been removed from items list
            # So we need to track this differently
    
    # Stop all active timers
    if 'timeouts' in giveaway:
        for item_id, timeout_info in giveaway['timeouts'].items():
            if 'timer' in timeout_info:
                timeout_info['timer'].cancel()
    
    # Stop recurring timer if exists
    if 'recurring_timer' in giveaway:
        giveaway['recurring_timer'].cancel()
        del giveaway['recurring_timer']
    
    # Remove from active giveaways
    active_giveaways = [g for g in active_giveaways if g['id'] != giveaway_id]
    giveaway['status'] = 'stopped'
    save_giveaways()
    
    # Announce giveaway removal with statistics
    remaining_items = len(giveaway['items'])
    message = f"Giveaway '{giveaway['name']}' has been stopped. "
    message += f"Items remaining: {remaining_items}"
    if payitforward_count > 0:
        message += f", Pay-it-forwards: {payitforward_count}"
    
    socketio.emit('admin_action_notification', {
        'action': 'giveaway_stopped',
        'message': f"⏹️ Giveaway '{giveaway['name']}' stopped - {remaining_items} items remaining",
        'timestamp': datetime.now().isoformat()
    })
    
    socketio.emit('giveaway_stopped', {
        'giveaway_id': giveaway_id,
        'giveaway_name': giveaway['name']
    })
    
    return jsonify({'success': True})

@app.route('/api/giveaways/<giveaway_id>/pause', methods=['POST'])
def pause_giveaway(giveaway_id):
    """Pause a giveaway (admin only)"""
    if not is_admin():
        return jsonify({'error': 'Not authorized'}), 401
    
    global active_giveaways
    
    # Find giveaway in either active_giveaways or main giveaways list
    giveaway = next((g for g in active_giveaways if g['id'] == giveaway_id), None)
    if not giveaway:
        giveaway = next((g for g in giveaways if g['id'] == giveaway_id), None)
    
    if not giveaway:
        return jsonify({'error': 'Giveaway not found'}), 404
    
    if giveaway['status'] != 'active':
        return jsonify({'error': 'Giveaway is not active'}), 400
    
    # Pause all active timers
    if 'timeouts' in giveaway:
        for item_id, timeout_info in giveaway['timeouts'].items():
            if 'timer' in timeout_info:
                timeout_info['timer'].cancel()
    
    # Pause recurring timer if exists
    if 'recurring_timer' in giveaway:
        giveaway['recurring_timer'].cancel()
        del giveaway['recurring_timer']
    
    # Remove from active giveaways temporarily
    active_giveaways = [g for g in active_giveaways if g['id'] != giveaway_id]
    giveaway['status'] = 'paused'
    save_giveaways()
    
    socketio.emit('admin_action_notification', {
        'action': 'giveaway_paused',
        'message': f"⏸️ Giveaway '{giveaway['name']}' paused - {len(giveaway['items'])} items remaining",
        'timestamp': datetime.now().isoformat()
    })
    
    socketio.emit('giveaway_paused', {
        'giveaway_id': giveaway_id,
        'giveaway_name': giveaway['name']
    })
    
    return jsonify({'success': True})

def is_admin():
    """Check if current session is admin"""
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')
    browser_id = f"{client_ip}_{user_agent}"
    
    # Check if this specific browser has admin access
    is_admin_result = browser_id in browser_admin_sessions
    
    # Debug logging
    print(f"🔐 Admin Check: {browser_id} -> {is_admin_result}")
    print(f"   Available sessions: {list(browser_admin_sessions.keys())}")
    
    return is_admin_result

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    # Use the same IP detection logic as get_client_ip() for consistency
    client_ip = get_client_ip()
    user_agent = request.environ.get('HTTP_USER_AGENT', '')
    
    connected_clients.add(client_ip)
    join_room('main')
    join_room(client_ip)  # Join room based on IP for targeted notifications
    
    # Check if this connection is from an admin based on session
    is_admin_connection = is_admin()
    if is_admin_connection:
        admin_connected_clients.add(client_ip)
    
    # Debug logging
    print(f"🔌 Client connected: IP {client_ip}, is_admin: {is_admin_connection}")
    print(f"   User-Agent: {user_agent[:50]}...")
    print(f"   Current connected_clients: {list(connected_clients)}")
    print(f"   Current admin_connected_clients: {list(admin_connected_clients)}")
    
    # Join admin room if admin
    if is_admin_connection:
        join_room('admin')
    
    emit('current_state', {
        'question': current_question,
        'comment': current_comment,
        'video_source': current_video_source,
        'is_admin': is_admin_connection
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    # Use the same IP detection logic as get_client_ip() for consistency
    client_ip = get_client_ip()
    user_agent = request.environ.get('HTTP_USER_AGENT', '')
    
    connected_clients.discard(client_ip)
    admin_connected_clients.discard(client_ip)
    leave_room('main')
    leave_room(client_ip)  # Leave IP-specific room
    
    # Debug logging
    print(f"🔌 Client disconnected: IP {client_ip}")
    print(f"   Remaining connected_clients: {list(connected_clients)}")
    print(f"   Remaining admin_connected_clients: {list(admin_connected_clients)}")

@socketio.on('admin_status_update')
def handle_admin_status_update():
    """Handle admin status update when user logs in/out"""
    # Use the same IP detection logic as get_client_ip() for consistency
    client_ip = get_client_ip()
    user_agent = request.environ.get('HTTP_USER_AGENT', '')
    
    # Check if this connection is from an admin based on session
    is_admin_connection = is_admin()
    
    if is_admin_connection:
        admin_connected_clients.add(client_ip)
        join_room('admin')
        print(f"🔐 Admin status updated: IP {client_ip} is now admin")
    else:
        admin_connected_clients.discard(client_ip)
        leave_room('admin')
        print(f"🔐 Admin status updated: IP {client_ip} is no longer admin")
    
    # Emit updated state
    emit('current_state', {
        'question': current_question,
        'comment': current_comment,
        'video_source': current_video_source,
        'is_admin': is_admin_connection
    })

@socketio.on('admin_action')
def handle_admin_action(data):
    """Handle admin actions via Socket.IO"""
    if not is_admin():
        emit('error', {'message': 'Not authorized'})
        return
    
    action = data.get('action')
    if action == 'accept_question':
        question_id = data.get('question_id')
        # Handle question acceptance
        emit('question_accepted', {'id': question_id}, room='main')
    elif action == 'delete_question':
        question_id = data.get('question_id')
        emit('question_deleted', {'id': question_id}, room='main')

if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Load giveaways on startup
    giveaways.extend(load_giveaways())
    
    # Run the server
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
