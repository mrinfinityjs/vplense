# vpLense Giveaway System

**Version 1.0** - Production Ready

A comprehensive giveaway system for the vpLense streaming application that allows admins to create, manage, and execute giveaways with real-time winner selection and pay-it-forward functionality.

## Features

### Admin Features
- **Create Giveaways**: Set up giveaways with custom names, timing, and settings
- **Schedule Giveaways**: Set delays (5min, 10min, 30min, 60min) or start immediately
- **Recurring Giveaways**: Configure giveaways to repeat every 5min, 10min, 30min, or 60min
- **Item Management**: Add and remove items from giveaways
- **Real-time Management**: Live updates and notifications for all giveaway activities

### Client Features
- **Winner Notifications**: Real-time popup when selected as a winner
- **Accept/Pay It Forward**: Choose to accept the prize or pay it forward to another user
- **Timeout Handling**: Automatic pay-it-forward if no response within timeout period
- **Prize Details**: View detailed information about won items

### System Features
- **IP-based Limits**: Configurable limits on prizes per IP address
- **Pay-it-Forward Chain**: Items can be passed to multiple users with configurable limits
- **Timeout Management**: Automatic handling of unresponsive winners
- **Real-time Notifications**: Live feed updates for all giveaway activities

## Configuration

The giveaway system uses the following configuration options in `config.json`:

```json
{
  "give_away_max_prize_per_ip": "2:64800",
  "give_away_item_timeout": "30",
  "give_away_max_payitforwards": "3"
}
```

### Configuration Options

- **`give_away_max_prize_per_ip`**: Maximum number of prizes a single IP can win within the time window (format: "count:seconds")
- **`give_away_item_timeout`**: Time in seconds for winners to respond before automatic pay-it-forward
- **`give_away_max_payitforwards`**: Maximum number of pay-it-forwards before an item is removed

## API Endpoints

### Giveaway Management
- `GET /api/giveaways` - Get all giveaways
- `POST /api/giveaways` - Create a new giveaway (admin only)
- `DELETE /api/giveaways/<id>` - Delete a giveaway (admin only)

### Item Management
- `POST /api/giveaways/<id>/items` - Add item to giveaway (admin only)
- `DELETE /api/giveaways/<id>/items/<item_id>` - Remove item from giveaway (admin only)

### Winner Actions
- `POST /api/giveaways/<id>/accept` - Accept a giveaway item (winner only)
- `POST /api/giveaways/<id>/payitforward` - Pay it forward (winner only)

## Usage

### Creating a Giveaway

1. **Admin Login**: Log in as admin using the admin panel
2. **Open Giveaway Manager**: Click the gift icon in the admin bar
3. **Configure Giveaway**:
   - Enter giveaway name
   - Select delay (immediate, 5min, 10min, 30min, 60min)
   - Choose recurring interval (if desired)
   - Set removal behavior
4. **Add Items**: Add prize items with names and optional links
5. **Create**: Click "Create Giveaway" to start

### Winner Experience

1. **Winner Selection**: When selected as a winner, a popup appears
2. **Response Time**: Winner has 30 seconds (configurable) to respond
3. **Choose Action**:
   - **Accept**: Claim the prize and view details
   - **Pay It Forward**: Pass the prize to another random user
4. **Prize Details**: If accepted, view detailed information about the prize

### Pay-it-Forward System

- Items can be passed to multiple users
- Each pay-it-forward increments a counter
- When max pay-it-forwards is reached, the item is removed
- All clients are notified of pay-it-forward actions

## Real-time Events

The system uses Socket.IO for real-time communication:

### Client Events
- `giveaway_winner_selected` - Notify winner of selection
- `giveaway_item_details` - Show prize details to winner
- `giveaway_pay_it_forward` - Notify of pay-it-forward action
- `giveaway_no_winner` - No eligible winners found
- `giveaway_item_removed` - Item removed from giveaway
- `giveaway_ended` - Giveaway has ended

### Admin Events
- `giveaway_created` - New giveaway created
- `giveaway_deleted` - Giveaway deleted
- `giveaway_item_added` - Item added to giveaway
- `giveaway_item_deleted` - Item removed from giveaway

## Data Storage

Giveaways are stored in `data/giveaways.json` with the following structure:

```json
[
  {
    "id": "uuid",
    "name": "Giveaway Name",
    "items": [
      {
        "id": "uuid",
        "name": "Item Name",
        "link": "https://example.com",
        "added_at": "2024-01-01T00:00:00"
      }
    ],
    "recurring": false,
    "recurring_interval": 0,
    "remove_on_accept": true,
    "created_at": "2024-01-01T00:00:00",
    "status": "active"
  }
]
```

## Security Features

- **Admin-only Management**: Only admins can create, modify, or delete giveaways
- **IP-based Limits**: Prevents single users from winning multiple prizes
- **Winner Verification**: Only the selected winner can accept or pay forward
- **Timeout Protection**: Automatic handling of unresponsive winners

## Testing

Run the test script to verify the giveaway system:

```bash
# Using uv (recommended)
uv run python test_scripts/test_giveaway.py

# Or traditional method
python test_scripts/test_giveaway.py
```

This will test:
- Giveaway creation
- Item management
- API endpoints
- Data persistence

## Troubleshooting

### Common Issues

1. **No Winners Selected**: Ensure there are connected clients (excluding admins)
2. **Giveaway Not Starting**: Check delay settings and server logs
3. **Items Not Appearing**: Verify giveaway has items added
4. **Timeout Issues**: Check `give_away_item_timeout` configuration

### Debug Information

- Check server logs for giveaway-related messages
- Verify client connections in the admin panel
- Monitor the Live Feed for giveaway notifications
- Check giveaway status in the admin interface

## Future Enhancements

Potential improvements for the giveaway system:

- **Custom Timeouts**: Per-giveaway timeout settings
- **Prize Categories**: Organize items by categories
- **Winner History**: Track all winners and their prizes
- **Analytics**: Detailed statistics on giveaway performance
- **Custom Notifications**: Personalized winner messages
- **Bulk Operations**: Manage multiple giveaways simultaneously
