# vpLense Quick Start Guide

**Version 1.0** - Production Ready

Get up and running with vpLense in minutes!

## 🚀 Quick Installation

### **Option 1: Automated Installation**
```bash
# Clone the repository
git clone https://github.com/mrinfinityjs/vplense.git
cd vplense

# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Run the installation script
chmod +x install.sh
./install.sh

# Start vpLense with uv
uv run python server.py
```

### **Option 2: Manual Installation**
```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Create data directories
mkdir -p data access

# Copy configuration
cp config.json.example config.json

# Install dependencies with uv
uv pip install -r requirements.txt

# Start vpLense with uv
uv run python server.py
```

## 🎯 First Steps

### **1. Access the Platform**
- Open your browser to `http://localhost:5000`
- You'll see the vpLense interface with the privacy debate demo content

### **2. Admin Login**
- Click on the logo or use the Konami code (↑↑↓↓←→←→)
- Enter password: `admin`
- You'll now see the admin toolbar at the bottom

### **3. Explore Features**

#### **As a Viewer:**
- **Ask Questions**: Use the question icon to submit questions
- **Make Comments**: Use the comment icon to share thoughts
- **View Topics**: Check current discussion topics
- **Participate in Giveaways**: Enter giveaways when available

#### **As an Admin:**
- **Moderate Content**: Review and approve questions/comments
- **Manage Giveaways**: Create and manage prize distributions
- **Monitor Activity**: Watch the live feed for real-time updates
- **Configure Settings**: Adjust system behavior

## 🎁 Giveaway System Demo

### **Create a Giveaway:**
1. Click the gift icon (🎁) in the admin bar
2. Enter giveaway name (e.g., "Privacy Protection Kit")
3. Select delay (immediate, 5min, 10min, 30min, 60min)
4. Choose recurring options if desired
5. Click "Create Giveaway"

### **Add Prizes:**
1. In the giveaway management panel
2. Click "Add Item" for any giveaway
3. Enter item name and optional link
4. Click "Add Item"

### **Winner Selection:**
- Winners are selected automatically when giveaways run
- Winners receive real-time notifications
- They can accept prizes or pay them forward
- All actions are logged in the live feed

## ⚙️ Configuration

### **Basic Settings**
Edit `config.json` to customize:

```json
{
  "app_name": "vpLense",
  "admin_password": "your_secure_password",
  "rate_limit_global": "30:5",
  "rate_limit_per_ip": "3:30"
}
```

### **Giveaway Settings**
```json
{
  "give_away_max_prize_per_ip": "2:64800",
  "give_away_item_timeout": "30",
  "give_away_max_payitforwards": "3"
}
```

## 🎬 Demo Content

The platform comes pre-loaded with privacy debate content:

- **8 Topics**: Data Privacy, Surveillance Capitalism, etc.
- **10 Questions**: Thought-provoking privacy questions
- **15 Comments**: Diverse viewpoints on privacy
- **1 Giveaway**: "Privacy Protection Kit" with 3 prizes

## 🔧 Common Tasks

### **Reset Demo Data**
```bash
# Login as admin, then use the reset button
# Or via API:
curl -X POST http://localhost:5000/api/admin/reset -b cookies.txt
```

### **Add New Content**
- **Topics**: Use the admin interface or API
- **Questions**: Submit via the question interface
- **Comments**: Submit via the comment interface
- **Giveaways**: Use the giveaway management panel

### **Monitor Activity**
- **Live Feed**: Real-time updates of all activities
- **Statistics**: View engagement metrics
- **Admin Notifications**: Special alerts for admins

## 🛠️ Troubleshooting

### **Common Issues**

#### **Port Already in Use**
```bash
# Kill existing processes
pkill -f "python server.py"
# Or use a different port
python server.py --port 5001
```

#### **Permission Denied**
```bash
# Make install script executable
chmod +x install.sh
```

#### **Module Not Found**
```bash
# Reinstall uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
# Reinstall requirements with uv
uv pip install -r requirements.txt
```

### **Getting Help**
- Check the full README.md for detailed documentation
- Review FEATURES.md for comprehensive feature overview
- Check server logs for error messages
- Ensure all dependencies are installed correctly

## 🎯 Next Steps

### **Customize for Your Stream**
1. **Change App Name**: Update `app_name` in config.json
2. **Set Admin Password**: Change `admin_password` in config.json
3. **Add Your Content**: Replace demo content with your topics/questions
4. **Configure Giveaways**: Set up prizes relevant to your stream
5. **Adjust Settings**: Fine-tune rate limits and timeouts

### **Production Deployment**
1. **Secure Configuration**: Use strong passwords and secure settings
2. **Domain Setup**: Configure proper domain and SSL certificates
3. **Backup Strategy**: Set up regular data backups
4. **Monitoring**: Implement system monitoring and logging
5. **Updates**: Keep dependencies updated for security

## 🎉 You're Ready!

vpLense is now running and ready for your streaming needs. The platform provides:

- ✅ Anonymous viewer interaction
- ✅ Real-time question/comment system
- ✅ Advanced giveaway management
- ✅ Comprehensive admin tools
- ✅ Privacy-focused design
- ✅ Mobile-responsive interface

**Happy Streaming with vpLense!** 🚀
