# vpLense - Verified Privacy Lense

![vpLense](vplense.png)

**vpLense** is a privacy-focused streaming interaction platform that enables anonymous viewer engagement for Twitch, YouTube, and other streaming platforms.

## What is vpLense?

vpLense provides a secure, anonymous interaction layer that enhances viewer engagement without compromising privacy. Viewers can ask questions, make suggestions, and participate in giveaways while maintaining complete anonymity.

## Core Functionality

### Anonymous Interaction System
- **No Registration Required**: Immediate participation without personal information
- **IP-based Rate Limiting**: Prevents abuse while maintaining privacy
- **Real-time Communication**: Live updates via Socket.IO

### Question & Answer System
- **Anonymous Question Submission**: Viewers submit questions without revealing identity
- **Live Question Display**: Questions appear on screen for streamers to address
- **Moderation Tools**: Accept, reject, or answer questions in real-time
- **Question History**: Track answered questions for reference

### Comment & Suggestion System
- **Instant Feedback**: Viewers provide comments and suggestions
- **Live Moderation**: Real-time approval/rejection system
- **Comment History**: Maintain records of accepted comments

### Advanced Giveaway System
- **Random Winner Selection**: Fair, algorithm-based winner selection
- **IP-based Limits**: Prevent single users from winning multiple prizes
- **Pay-it-Forward System**: Winners can pass prizes to other viewers
- **Timeout Management**: Automatic handling of unresponsive winners
- **Recurring Giveaways**: Automatic repetition every 5-60 minutes

### Admin & Moderation Tools
- **Real-time Moderation**: Live approval/rejection of content
- **IP Access Control**: Whitelist/blacklist management
- **Rate Limiting**: Prevent spam and abuse
- **Auto-ACL System**: Automatic access control based on behavior
- **Live Statistics**: Real-time engagement metrics
- **System Configuration**: Adjust rate limits, timeouts, and behavior

## Project Structure

```
vplense/
├── server.py              # Main Flask application
├── templates/
│   └── index.html         # Vue.js frontend interface
├── data/                  # JSON data storage
│   ├── questions.json
│   ├── comments_accepted.json
│   ├── giveaways.json
│   └── topics.json
├── access/                # IP access control
│   ├── white_list.json
│   └── black_list.json
├── docs/                  # Documentation
├── test_scripts/          # Test files
├── config.json.example    # Configuration template
└── requirements.txt       # Python dependencies
```

## Quick Setup

### Prerequisites
- Python 3.8+
- uv (fast Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/mrinfinityjs/vplense.git
   cd vplense
   ```

2. **Install uv**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source $HOME/.cargo/env
   ```

3. **Install dependencies**
   ```bash
   uv pip install -r requirements.txt
   ```

4. **Configure settings**
   ```bash
   cp config.json.example config.json
   # Edit config.json with your settings
   ```

5. **Run the application**
   ```bash
   uv run python server.py
   ```

6. **Access the platform**
   - Open browser to `http://localhost:5000`
   - Admin login: Use password from config.json

## Configuration

Edit `config.json` to customize:

```json
{
  "app_name": "Your Stream Name",
  "admin_password": "your_secure_password",
  "rate_limit_global": "30:5",
  "rate_limit_per_ip": "3:30",
  "give_away_max_prize_per_ip": "2:64800",
  "give_away_item_timeout": "30",
  "give_away_max_payitforwards": "3"
}
```

## Production Deployment

### Using Caddy

1. **Install Caddy**
   ```bash
   # Debian/Ubuntu
   sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
   sudo apt update
   sudo apt install caddy

   # Fedora
   sudo dnf install 'dnf-command(copr)'
   sudo dnf copr enable @caddy/caddy
   sudo dnf install caddy
   ```

2. **Create Caddyfile**
   ```caddy
   yourdomain.com {
       reverse_proxy localhost:5000
       
       # WebSocket support
       reverse_proxy /socket.io/* localhost:5000 {
           header_up Host {host}
           header_up X-Real-IP {remote}
           header_up X-Forwarded-For {remote}
           header_up X-Forwarded-Proto {scheme}
       }
   }
   ```

3. **Start services**
   ```bash
   # Start vpLense
   uv run python server.py &
   
   # Start Caddy
   sudo systemctl enable caddy
   sudo systemctl start caddy
   ```

## Usage

### For Viewers
1. Access the vpLense URL
2. Ask questions using the question interface
3. Make comments and suggestions
4. Participate in giveaways when available
5. Stay completely anonymous

### For Streamers/Admins
1. Login with admin credentials
2. Review and approve questions/comments
3. Create and manage giveaways
4. Monitor live feed for real-time updates
5. Configure system settings as needed

## API Documentation

Complete API reference available in `docs/API.md`

## Features Documentation

Detailed feature descriptions available in `docs/FEATURES.md`

## Testing

Run test scripts to verify functionality:

```bash
# Test giveaway system
uv run python test_scripts/test_giveaway.py

# Test rate limiting
uv run python test_scripts/test_rate_limits.py
```

## License

MIT License - see LICENSE file for details

## Repository

https://github.com/mrinfinityjs/vplense
