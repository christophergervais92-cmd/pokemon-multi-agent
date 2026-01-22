#!/usr/bin/env python3
"""
Multi-Channel Notification System

Sends alerts via multiple channels:
- Discord (webhook + DM)
- SMS (Twilio)
- Push Notifications (Pushover/Pushbullet)
- Email (SMTP/SendGrid)
- Telegram
- Webhook (generic)

Users can configure their preferred channels and priority levels.

Usage:
    from notifications.multi_channel import NotificationManager
    
    manager = NotificationManager()
    manager.send_restock_alert(product, user)
"""
import os
import sys
import json
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

try:
    import requests
except ImportError:
    requests = None

# =============================================================================
# CONFIGURATION
# =============================================================================

# Twilio (SMS)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")

# Pushover (Push Notifications)
PUSHOVER_APP_TOKEN = os.environ.get("PUSHOVER_APP_TOKEN", "")
PUSHOVER_USER_KEY = os.environ.get("PUSHOVER_USER_KEY", "")

# Pushbullet (Push Notifications)
PUSHBULLET_API_KEY = os.environ.get("PUSHBULLET_API_KEY", "")

# SendGrid (Email)
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "alerts@lotcg.com")

# SMTP (Email fallback)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Discord
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")

# Database for user preferences
NOTIFICATIONS_DB = Path(__file__).parent.parent.parent / "notifications.db"

# Alert priority levels
PRIORITY_CRITICAL = "critical"  # Restock, limited drop
PRIORITY_HIGH = "high"          # Price drop >20%
PRIORITY_NORMAL = "normal"      # Watchlist match
PRIORITY_LOW = "low"            # Market update


# =============================================================================
# DATABASE
# =============================================================================

def init_notifications_db():
    """Initialize the notifications database."""
    conn = sqlite3.connect(str(NOTIFICATIONS_DB))
    cursor = conn.cursor()
    
    # User notification preferences
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT UNIQUE,
            
            -- Contact methods
            phone_number TEXT,
            email TEXT,
            pushover_user_key TEXT,
            pushbullet_device TEXT,
            telegram_chat_id TEXT,
            webhook_url TEXT,
            
            -- Preferences
            sms_enabled BOOLEAN DEFAULT 0,
            email_enabled BOOLEAN DEFAULT 0,
            push_enabled BOOLEAN DEFAULT 0,
            telegram_enabled BOOLEAN DEFAULT 0,
            discord_dm_enabled BOOLEAN DEFAULT 1,
            
            -- Priority thresholds (only send above this level)
            sms_min_priority TEXT DEFAULT 'critical',
            email_min_priority TEXT DEFAULT 'high',
            push_min_priority TEXT DEFAULT 'high',
            
            -- Quiet hours (24h format, e.g., "23:00-07:00")
            quiet_hours_start TEXT,
            quiet_hours_end TEXT,
            
            -- Rate limiting
            max_daily_sms INTEGER DEFAULT 10,
            max_daily_push INTEGER DEFAULT 50,
            sms_sent_today INTEGER DEFAULT 0,
            push_sent_today INTEGER DEFAULT 0,
            last_reset DATE,
            
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Notification log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT,
            channel TEXT,
            priority TEXT,
            message TEXT,
            product_id TEXT,
            status TEXT,
            error TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


init_notifications_db()


# =============================================================================
# SMS (TWILIO)
# =============================================================================

class TwilioSMS:
    """Send SMS via Twilio."""
    
    @staticmethod
    def is_available() -> bool:
        """Check if Twilio is configured."""
        return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER)
    
    @staticmethod
    def send(to_number: str, message: str) -> Dict[str, Any]:
        """
        Send an SMS message.
        
        Args:
            to_number: Phone number with country code (+1...)
            message: Message text (max 160 chars recommended)
        
        Returns:
            {"success": bool, "sid": "...", "error": "..."}
        """
        if not TwilioSMS.is_available():
            return {"success": False, "error": "Twilio not configured"}
        
        if not requests:
            return {"success": False, "error": "requests library not available"}
        
        try:
            response = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json",
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                data={
                    "From": TWILIO_PHONE_NUMBER,
                    "To": to_number,
                    "Body": message[:1600],  # Max SMS length
                },
                timeout=10,
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                return {"success": True, "sid": data.get("sid")}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


# =============================================================================
# PUSH NOTIFICATIONS
# =============================================================================

class Pushover:
    """Send push notifications via Pushover."""
    
    @staticmethod
    def is_available() -> bool:
        """Check if Pushover is configured."""
        return bool(PUSHOVER_APP_TOKEN)
    
    @staticmethod
    def send(
        user_key: str,
        title: str,
        message: str,
        url: str = None,
        priority: int = 0,
        sound: str = "pushover",
    ) -> Dict[str, Any]:
        """
        Send a Pushover notification.
        
        Args:
            user_key: User's Pushover key
            title: Notification title
            message: Notification body
            url: Optional URL to open
            priority: -2 to 2 (2 = emergency)
            sound: Sound name
        
        Returns:
            {"success": bool, "error": "..."}
        """
        if not Pushover.is_available():
            return {"success": False, "error": "Pushover not configured"}
        
        if not requests:
            return {"success": False, "error": "requests library not available"}
        
        try:
            data = {
                "token": PUSHOVER_APP_TOKEN,
                "user": user_key or PUSHOVER_USER_KEY,
                "title": title[:250],
                "message": message[:1024],
                "priority": priority,
                "sound": sound,
            }
            
            if url:
                data["url"] = url
                data["url_title"] = "View Deal"
            
            response = requests.post(
                "https://api.pushover.net/1/messages.json",
                data=data,
                timeout=10,
            )
            
            if response.status_code == 200:
                return {"success": True}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


class Pushbullet:
    """Send push notifications via Pushbullet."""
    
    @staticmethod
    def is_available() -> bool:
        """Check if Pushbullet is configured."""
        return bool(PUSHBULLET_API_KEY)
    
    @staticmethod
    def send(
        title: str,
        message: str,
        url: str = None,
        device_iden: str = None,
    ) -> Dict[str, Any]:
        """Send a Pushbullet notification."""
        if not Pushbullet.is_available():
            return {"success": False, "error": "Pushbullet not configured"}
        
        if not requests:
            return {"success": False, "error": "requests library not available"}
        
        try:
            headers = {"Access-Token": PUSHBULLET_API_KEY}
            
            if url:
                data = {
                    "type": "link",
                    "title": title,
                    "body": message,
                    "url": url,
                }
            else:
                data = {
                    "type": "note",
                    "title": title,
                    "body": message,
                }
            
            if device_iden:
                data["device_iden"] = device_iden
            
            response = requests.post(
                "https://api.pushbullet.com/v2/pushes",
                headers=headers,
                json=data,
                timeout=10,
            )
            
            if response.status_code in (200, 201):
                return {"success": True}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


# =============================================================================
# EMAIL
# =============================================================================

class EmailSender:
    """Send emails via SendGrid or SMTP."""
    
    @staticmethod
    def is_available() -> bool:
        """Check if email is configured."""
        return bool(SENDGRID_API_KEY or (SMTP_USER and SMTP_PASSWORD))
    
    @staticmethod
    def send(
        to_email: str,
        subject: str,
        body_text: str,
        body_html: str = None,
    ) -> Dict[str, Any]:
        """Send an email."""
        if SENDGRID_API_KEY:
            return EmailSender._send_sendgrid(to_email, subject, body_text, body_html)
        elif SMTP_USER and SMTP_PASSWORD:
            return EmailSender._send_smtp(to_email, subject, body_text, body_html)
        else:
            return {"success": False, "error": "Email not configured"}
    
    @staticmethod
    def _send_sendgrid(
        to_email: str,
        subject: str,
        body_text: str,
        body_html: str = None,
    ) -> Dict[str, Any]:
        """Send via SendGrid."""
        if not requests:
            return {"success": False, "error": "requests library not available"}
        
        try:
            content = [{"type": "text/plain", "value": body_text}]
            if body_html:
                content.append({"type": "text/html", "value": body_html})
            
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": SENDGRID_FROM_EMAIL, "name": "LO TCG Alerts"},
                    "subject": subject,
                    "content": content,
                },
                timeout=10,
            )
            
            if response.status_code in (200, 201, 202):
                return {"success": True}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _send_smtp(
        to_email: str,
        subject: str,
        body_text: str,
        body_html: str = None,
    ) -> Dict[str, Any]:
        """Send via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_USER
            msg["To"] = to_email
            
            msg.attach(MIMEText(body_text, "plain"))
            if body_html:
                msg.attach(MIMEText(body_html, "html"))
            
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# =============================================================================
# TELEGRAM
# =============================================================================

class Telegram:
    """Send messages via Telegram bot."""
    
    @staticmethod
    def is_available() -> bool:
        """Check if Telegram is configured."""
        return bool(TELEGRAM_BOT_TOKEN)
    
    @staticmethod
    def send(
        chat_id: str,
        message: str,
        parse_mode: str = "HTML",
    ) -> Dict[str, Any]:
        """Send a Telegram message."""
        if not Telegram.is_available():
            return {"success": False, "error": "Telegram not configured"}
        
        if not requests:
            return {"success": False, "error": "requests library not available"}
        
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": parse_mode,
                },
                timeout=10,
            )
            
            if response.status_code == 200:
                return {"success": True}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


# =============================================================================
# DISCORD DM
# =============================================================================

class DiscordDM:
    """Send Discord direct messages."""
    
    @staticmethod
    def is_available() -> bool:
        """Check if Discord bot is configured."""
        return bool(DISCORD_BOT_TOKEN)
    
    @staticmethod
    def send(user_id: str, message: str, embed: Dict = None) -> Dict[str, Any]:
        """
        Send a Discord DM.
        
        Note: The user must share a server with the bot.
        """
        if not DiscordDM.is_available():
            return {"success": False, "error": "Discord bot not configured"}
        
        if not requests:
            return {"success": False, "error": "requests library not available"}
        
        try:
            # First, create a DM channel
            response = requests.post(
                "https://discord.com/api/v10/users/@me/channels",
                headers={
                    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={"recipient_id": user_id},
                timeout=10,
            )
            
            if response.status_code not in (200, 201):
                return {"success": False, "error": f"Could not create DM: {response.text}"}
            
            channel_id = response.json()["id"]
            
            # Send the message
            payload = {"content": message}
            if embed:
                payload["embeds"] = [embed]
            
            response = requests.post(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers={
                    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10,
            )
            
            if response.status_code in (200, 201):
                return {"success": True}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


# =============================================================================
# NOTIFICATION MANAGER
# =============================================================================

class NotificationManager:
    """
    Unified notification manager.
    
    Routes alerts to appropriate channels based on user preferences.
    """
    
    def __init__(self):
        """Initialize the manager."""
        self.sms = TwilioSMS()
        self.pushover = Pushover()
        self.pushbullet = Pushbullet()
        self.email = EmailSender()
        self.telegram = Telegram()
        self.discord = DiscordDM()
    
    def get_user_prefs(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """Get user notification preferences."""
        conn = sqlite3.connect(str(NOTIFICATIONS_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM user_notifications WHERE discord_id = ?",
            (discord_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def update_user_prefs(self, discord_id: str, **kwargs) -> bool:
        """Update user notification preferences."""
        conn = sqlite3.connect(str(NOTIFICATIONS_DB))
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute(
            "SELECT id FROM user_notifications WHERE discord_id = ?",
            (discord_id,)
        )
        exists = cursor.fetchone()
        
        if exists:
            # Update
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [discord_id]
            cursor.execute(
                f"UPDATE user_notifications SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE discord_id = ?",
                values
            )
        else:
            # Insert
            kwargs["discord_id"] = discord_id
            cols = ", ".join(kwargs.keys())
            placeholders = ", ".join(["?"] * len(kwargs))
            cursor.execute(
                f"INSERT INTO user_notifications ({cols}) VALUES ({placeholders})",
                list(kwargs.values())
            )
        
        conn.commit()
        conn.close()
        return True
    
    def send_alert(
        self,
        discord_id: str,
        title: str,
        message: str,
        priority: str = PRIORITY_NORMAL,
        url: str = None,
        product_data: Dict = None,
    ) -> Dict[str, Any]:
        """
        Send an alert through all enabled channels for a user.
        
        Args:
            discord_id: User's Discord ID
            title: Alert title
            message: Alert body
            priority: Alert priority level
            url: Optional action URL
            product_data: Optional product details
        
        Returns:
            {"channels": {"sms": {...}, "push": {...}, ...}}
        """
        prefs = self.get_user_prefs(discord_id)
        results = {"channels": {}}
        
        # Always try Discord DM
        if prefs is None or prefs.get("discord_dm_enabled", True):
            embed = self._create_discord_embed(title, message, priority, url, product_data)
            result = self.discord.send(discord_id, message, embed)
            results["channels"]["discord_dm"] = result
            self._log_notification(discord_id, "discord_dm", priority, message, result)
        
        if prefs is None:
            return results
        
        # Check quiet hours
        if self._is_quiet_hours(prefs):
            results["quiet_hours"] = True
            return results
        
        # SMS (only for critical/high)
        if prefs.get("sms_enabled") and prefs.get("phone_number"):
            if self._meets_priority(priority, prefs.get("sms_min_priority", "critical")):
                if prefs.get("sms_sent_today", 0) < prefs.get("max_daily_sms", 10):
                    sms_msg = f"🔥 {title}: {message[:100]}"
                    if url:
                        sms_msg += f"\n{url}"
                    result = self.sms.send(prefs["phone_number"], sms_msg)
                    results["channels"]["sms"] = result
                    self._log_notification(discord_id, "sms", priority, sms_msg, result)
                    self._increment_counter(discord_id, "sms")
        
        # Push notifications
        if prefs.get("push_enabled"):
            if self._meets_priority(priority, prefs.get("push_min_priority", "high")):
                if prefs.get("pushover_user_key"):
                    pushover_priority = 1 if priority == PRIORITY_CRITICAL else 0
                    result = self.pushover.send(
                        prefs["pushover_user_key"],
                        title,
                        message,
                        url,
                        pushover_priority,
                        "magic" if priority == PRIORITY_CRITICAL else "pushover",
                    )
                    results["channels"]["pushover"] = result
                    self._log_notification(discord_id, "pushover", priority, message, result)
                
                if prefs.get("pushbullet_device") or PUSHBULLET_API_KEY:
                    result = self.pushbullet.send(
                        title,
                        message,
                        url,
                        prefs.get("pushbullet_device"),
                    )
                    results["channels"]["pushbullet"] = result
                    self._log_notification(discord_id, "pushbullet", priority, message, result)
        
        # Email
        if prefs.get("email_enabled") and prefs.get("email"):
            if self._meets_priority(priority, prefs.get("email_min_priority", "high")):
                html = self._create_email_html(title, message, priority, url, product_data)
                result = self.email.send(
                    prefs["email"],
                    f"[LO TCG] {title}",
                    message,
                    html,
                )
                results["channels"]["email"] = result
                self._log_notification(discord_id, "email", priority, message, result)
        
        # Telegram
        if prefs.get("telegram_enabled") and prefs.get("telegram_chat_id"):
            emoji = "🚨" if priority == PRIORITY_CRITICAL else "📢"
            telegram_msg = f"{emoji} <b>{title}</b>\n\n{message}"
            if url:
                telegram_msg += f"\n\n<a href='{url}'>View Deal</a>"
            result = self.telegram.send(prefs["telegram_chat_id"], telegram_msg)
            results["channels"]["telegram"] = result
            self._log_notification(discord_id, "telegram", priority, telegram_msg, result)
        
        return results
    
    def send_restock_alert(
        self,
        product: Dict[str, Any],
        user_ids: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a restock alert to specified users or all watching users.
        
        Args:
            product: Product data with name, price, url, retailer
            user_ids: List of Discord user IDs (None = all watchers)
        
        Returns:
            {"sent_to": [...], "results": {...}}
        """
        title = f"🔥 RESTOCK: {product.get('name', 'Product')}"
        message = (
            f"{product.get('name', 'Product')} is back in stock!\n"
            f"💰 Price: ${product.get('price', 'N/A')}\n"
            f"🏪 Retailer: {product.get('retailer', 'Unknown')}"
        )
        
        results = {"sent_to": [], "results": {}}
        
        if user_ids is None:
            # Would query watchlist DB for users watching this product
            # For now, use provided list
            user_ids = []
        
        for user_id in user_ids:
            result = self.send_alert(
                user_id,
                title,
                message,
                PRIORITY_CRITICAL,
                product.get("url"),
                product,
            )
            results["sent_to"].append(user_id)
            results["results"][user_id] = result
        
        return results
    
    def send_price_drop_alert(
        self,
        product: Dict[str, Any],
        old_price: float,
        new_price: float,
        user_ids: List[str],
    ) -> Dict[str, Any]:
        """Send price drop alert."""
        drop_pct = ((old_price - new_price) / old_price) * 100
        
        priority = PRIORITY_HIGH if drop_pct > 20 else PRIORITY_NORMAL
        
        title = f"💸 Price Drop: {product.get('name', 'Product')}"
        message = (
            f"{product.get('name', 'Product')} dropped {drop_pct:.0f}%!\n"
            f"💰 Was: ${old_price:.2f} → Now: ${new_price:.2f}\n"
            f"🏪 {product.get('retailer', 'Unknown')}"
        )
        
        results = {"sent_to": [], "results": {}}
        
        for user_id in user_ids:
            result = self.send_alert(
                user_id,
                title,
                message,
                priority,
                product.get("url"),
                product,
            )
            results["sent_to"].append(user_id)
            results["results"][user_id] = result
        
        return results
    
    def _meets_priority(self, alert_priority: str, min_priority: str) -> bool:
        """Check if alert priority meets minimum threshold."""
        levels = {
            PRIORITY_LOW: 0,
            PRIORITY_NORMAL: 1,
            PRIORITY_HIGH: 2,
            PRIORITY_CRITICAL: 3,
        }
        return levels.get(alert_priority, 1) >= levels.get(min_priority, 2)
    
    def _is_quiet_hours(self, prefs: Dict) -> bool:
        """Check if current time is in quiet hours."""
        start = prefs.get("quiet_hours_start")
        end = prefs.get("quiet_hours_end")
        
        if not start or not end:
            return False
        
        try:
            now = datetime.now().time()
            start_time = datetime.strptime(start, "%H:%M").time()
            end_time = datetime.strptime(end, "%H:%M").time()
            
            if start_time < end_time:
                return start_time <= now <= end_time
            else:  # Overnight (e.g., 23:00 - 07:00)
                return now >= start_time or now <= end_time
        except:
            return False
    
    def _increment_counter(self, discord_id: str, channel: str):
        """Increment daily send counter."""
        conn = sqlite3.connect(str(NOTIFICATIONS_DB))
        cursor = conn.cursor()
        
        today = datetime.now().date().isoformat()
        
        # Reset if new day
        cursor.execute(
            "UPDATE user_notifications SET sms_sent_today = 0, push_sent_today = 0, last_reset = ? WHERE discord_id = ? AND (last_reset != ? OR last_reset IS NULL)",
            (today, discord_id, today)
        )
        
        # Increment
        if channel == "sms":
            cursor.execute(
                "UPDATE user_notifications SET sms_sent_today = sms_sent_today + 1 WHERE discord_id = ?",
                (discord_id,)
            )
        elif channel in ("pushover", "pushbullet"):
            cursor.execute(
                "UPDATE user_notifications SET push_sent_today = push_sent_today + 1 WHERE discord_id = ?",
                (discord_id,)
            )
        
        conn.commit()
        conn.close()
    
    def _log_notification(
        self,
        discord_id: str,
        channel: str,
        priority: str,
        message: str,
        result: Dict,
    ):
        """Log notification to database."""
        conn = sqlite3.connect(str(NOTIFICATIONS_DB))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notification_log (discord_id, channel, priority, message, status, error)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            discord_id,
            channel,
            priority,
            message[:500],
            "success" if result.get("success") else "failed",
            result.get("error"),
        ))
        
        conn.commit()
        conn.close()
    
    def _create_discord_embed(
        self,
        title: str,
        message: str,
        priority: str,
        url: str = None,
        product: Dict = None,
    ) -> Dict:
        """Create a Discord embed."""
        colors = {
            PRIORITY_CRITICAL: 0xFF0000,  # Red
            PRIORITY_HIGH: 0xFFA500,      # Orange
            PRIORITY_NORMAL: 0x00FF00,    # Green
            PRIORITY_LOW: 0x808080,       # Gray
        }
        
        embed = {
            "title": title,
            "description": message,
            "color": colors.get(priority, 0x00FF00),
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "LO TCG Alerts"},
        }
        
        if url:
            embed["url"] = url
        
        if product:
            embed["fields"] = []
            if product.get("retailer"):
                embed["fields"].append({
                    "name": "Retailer",
                    "value": product["retailer"],
                    "inline": True,
                })
            if product.get("price"):
                embed["fields"].append({
                    "name": "Price",
                    "value": f"${product['price']}",
                    "inline": True,
                })
            if product.get("image"):
                embed["thumbnail"] = {"url": product["image"]}
        
        return embed
    
    def _create_email_html(
        self,
        title: str,
        message: str,
        priority: str,
        url: str = None,
        product: Dict = None,
    ) -> str:
        """Create HTML email body."""
        bg_colors = {
            PRIORITY_CRITICAL: "#FF4444",
            PRIORITY_HIGH: "#FFA500",
            PRIORITY_NORMAL: "#44AA44",
            PRIORITY_LOW: "#888888",
        }
        
        button_html = ""
        if url:
            button_html = f'''
                <a href="{url}" style="display: inline-block; padding: 12px 24px; 
                   background: {bg_colors.get(priority, '#44AA44')}; color: white; 
                   text-decoration: none; border-radius: 6px; margin-top: 20px;">
                    View Deal →
                </a>
            '''
        
        product_html = ""
        if product:
            product_html = f'''
                <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>Product:</strong> {product.get('name', 'N/A')}</p>
                    <p><strong>Price:</strong> ${product.get('price', 'N/A')}</p>
                    <p><strong>Retailer:</strong> {product.get('retailer', 'N/A')}</p>
                </div>
            '''
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                     max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: {bg_colors.get(priority, '#44AA44')}; color: white; 
                        padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">{title}</h1>
            </div>
            <div style="background: white; padding: 20px; border: 1px solid #ddd; border-top: none;">
                <p style="font-size: 16px; line-height: 1.6;">{message}</p>
                {product_html}
                {button_html}
            </div>
            <div style="text-align: center; padding: 20px; color: #888; font-size: 12px;">
                <p>LO TCG Alerts • Manage settings in Discord with /settings</p>
            </div>
        </body>
        </html>
        '''
    
    def get_available_channels(self) -> Dict[str, bool]:
        """Get which notification channels are configured."""
        return {
            "sms": TwilioSMS.is_available(),
            "pushover": Pushover.is_available(),
            "pushbullet": Pushbullet.is_available(),
            "email": EmailSender.is_available(),
            "telegram": Telegram.is_available(),
            "discord_dm": DiscordDM.is_available(),
        }


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI for testing notifications."""
    manager = NotificationManager()
    
    print("Available channels:")
    print(json.dumps(manager.get_available_channels(), indent=2))
    
    # Demo alert
    print("\n--- Demo Alert ---")
    result = manager.send_alert(
        discord_id="123456789",
        title="Test Alert",
        message="This is a test notification from LO TCG",
        priority=PRIORITY_HIGH,
        url="https://example.com",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
