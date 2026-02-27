# Notifications Agent

**Backend**: `agents/notifications/multi_channel.py`

## Purpose
Multi-channel alert system sending restock, price drop, and market opportunity notifications via Discord, SMS, Telegram, email, and webhooks.

## API Endpoints
- `POST /notifications/send` - Send alert to user's configured channels
- `GET /notifications/channels` - List user's notification preferences
- `PUT /notifications/preferences` - Update alert settings

## Inputs / Outputs
**Input**: Alert type (restock/price_drop/market), product details, user preferences
**Output**: Delivery status per channel, read receipts, notification history

## Key Dependencies
- `discord_bot/notifier.py` - Discord message delivery
- `notifications/multi_channel.py` - Channel routing logic
- Twilio, SendGrid, Telegram, Pushover APIs for multi-channel delivery
