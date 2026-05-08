"""
JKT48 Stock Monitor - Background Worker
24/7 monitoring with Telegram notifications
Optimized version - WIB timezone only
"""

import requests
import json
import time
import os
from datetime import datetime, timezone, timedelta
import pytz

# Constants
WIB = pytz.timezone('Asia/Jakarta')
TELEGRAM_BOT_TOKEN = "8541605155:AAFlFyF1g2DkW-ZonmX2H_7S-k67n3JKjWE"
TELEGRAM_CHAT_ID = "824000905"

# Configuration
API_URL = "https://jkt48.com/api/v1/exclusives/EXBE10?lang=id"
REFRESH_INTERVAL = 30  # seconds
CHANGE_LOG_FILE = "/mnt/user-data/outputs/change_log.json"
PREVIOUS_DATA_FILE = "/mnt/user-data/outputs/previous_data.json"

def now_wib():
    """Get current time in WIB"""
    return datetime.now(WIB)

def format_event_date(api_date_str):
    """Convert API date to display format with +1 day offset"""
    try:
        date_obj = datetime.strptime(api_date_str, '%Y-%m-%d') + timedelta(days=1)
        return date_obj.strftime("%A, %d %B %Y")
    except:
        return api_date_str

def get_adjusted_event_date(api_date_str):
    """Get event date with +1 day offset"""
    try:
        date_obj = datetime.strptime(api_date_str, '%Y-%m-%d') + timedelta(days=1)
        return date_obj.strftime('%Y-%m-%d')
    except:
        return api_date_str

def send_telegram_notification(message):
    """Send notification via Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print(f"  ✅ Telegram notification sent")
            return True
        else:
            print(f"  ❌ Telegram failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Telegram error: {e}")
        return False

def fetch_api_data(cookies=None):
    """Fetch data from JKT48 API"""
    max_retries = 3
    retry_delay = 5
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://jkt48.com/exclusive'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(API_URL, headers=headers, cookies=cookies, timeout=15)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                print(f"  ⚠️  Received HTML - possible waiting room")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * 2)
                    continue
                return None
            
            data = response.json()
            if data.get('status') and data.get('data'):
                return data['data']
            
            return None
            
        except requests.exceptions.Timeout:
            print(f"  ⏱️  Timeout on attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None
            
        except Exception as e:
            print(f"  ❌ Error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None
    
    return None

def load_previous_data():
    """Load previous API data"""
    try:
        if os.path.exists(PREVIOUS_DATA_FILE):
            with open(PREVIOUS_DATA_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading previous data: {e}")
    return None

def save_previous_data(data):
    """Save current API data"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(PREVIOUS_DATA_FILE), exist_ok=True)
        
        with open(PREVIOUS_DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"  💾 Saved to {PREVIOUS_DATA_FILE}")
    except Exception as e:
        print(f"  ❌ Error saving previous data: {e}")

def load_change_log():
    """Load change log"""
    try:
        if os.path.exists(CHANGE_LOG_FILE):
            with open(CHANGE_LOG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading change log: {e}")
    return []

def save_change_log(changes):
    """Save change log (keep last 500 entries)"""
    try:
        if len(changes) > 500:
            changes = changes[-500:]
        
        with open(CHANGE_LOG_FILE, 'w') as f:
            json.dump(changes, f, indent=2)
    except Exception as e:
        print(f"Error saving change log: {e}")

def detect_changes(prev_data, new_data):
    """Detect stock changes between old and new data"""
    if not prev_data or not new_data:
        return []
    
    changes = []
    event_name = "We Are Love, Dream, Passion on Fire"
    
    prev_sessions = {(s['label'], s['date']): s for s in prev_data.get('session', [])}
    new_sessions = {(s['label'], s['date']): s for s in new_data.get('session', [])}
    
    for session_key, new_session in new_sessions.items():
        prev_session = prev_sessions.get(session_key)
        
        if not prev_session:
            continue
        
        # Get adjusted event date
        original_date = new_session.get('date', '')
        adjusted_date = get_adjusted_event_date(original_date)
        formatted_date = format_event_date(original_date)
        
        # Compare each member/lane
        prev_details = {d['label']: d for d in prev_session.get('detail', [])}
        new_details = {d['label']: d for d in new_session.get('detail', [])}
        
        for lane_label, new_detail in new_details.items():
            prev_detail = prev_details.get(lane_label)
            
            if not prev_detail:
                continue
            
            member = new_detail['jkt48_member_name']
            session_label = new_session['label']
            
            prev_sold = prev_detail.get('tickets_sold', 0)
            new_sold = new_detail.get('tickets_sold', 0)
            prev_available = prev_detail.get('available_quota', 0)
            new_available = new_detail.get('available_quota', 0)
            
            # 1. Stock Return (Sold Out → Available)
            if prev_available == 0 and new_available > 0:
                change = {
                    'type': 'stock_return',
                    'event': event_name,
                    'member': member,
                    'session': session_label,
                    'session_date': adjusted_date,
                    'session_date_display': formatted_date,
                    'returned_quota': new_available,
                    'refunded_tickets': prev_sold - new_sold if new_sold < prev_sold else 0,
                    'timestamp': now_wib().isoformat()
                }
                changes.append(change)
                
                # Always notify stock return
                msg = (
                    f"♻️ *STOCK KEMBALI!*\n\n"
                    f"📅 {formatted_date}\n"
                    f"🎭 {session_label}\n"
                    f"👤 {member}\n\n"
                    f"Sold Out → {new_available} tiket tersedia"
                )
                if change['refunded_tickets'] > 0:
                    msg += f"\n💳 {change['refunded_tickets']} transaksi dibatalkan"
                
                send_telegram_notification(msg)
            
            # 2. Stock Increase (not from sold out)
            elif new_available > prev_available and prev_available > 0:
                change = {
                    'type': 'stock_increase',
                    'event': event_name,
                    'member': member,
                    'session': session_label,
                    'session_date': adjusted_date,
                    'session_date_display': formatted_date,
                    'old_quota': prev_available,
                    'new_quota': new_available,
                    'difference': new_available - prev_available,
                    'timestamp': now_wib().isoformat()
                }
                changes.append(change)
                
                msg = (
                    f"📈 *STOCK NAIK!*\n\n"
                    f"📅 {formatted_date}\n"
                    f"🎭 {session_label}\n"
                    f"👤 {member}\n\n"
                    f"{prev_available} → {new_available} (+{change['difference']})"
                )
                send_telegram_notification(msg)
            
            # 3. New Transaction
            elif new_sold > prev_sold:
                sold_diff = new_sold - prev_sold
                change = {
                    'type': 'new_transaction',
                    'event': event_name,
                    'member': member,
                    'session': session_label,
                    'session_date': adjusted_date,
                    'session_date_display': formatted_date,
                    'tickets_bought': sold_diff,
                    'old_sold': prev_sold,
                    'new_sold': new_sold,
                    'remaining': new_available,
                    'timestamp': now_wib().isoformat()
                }
                changes.append(change)
                
                # Notify if significant (>=5 tickets) or sold out
                if sold_diff >= 5 or new_available == 0:
                    msg = (
                        f"🎫 *TRANSAKSI BARU!*\n\n"
                        f"📅 {formatted_date}\n"
                        f"🎭 {session_label}\n"
                        f"👤 {member}\n\n"
                        f"{sold_diff} tiket terjual\n"
                        f"Sisa: {new_available}"
                    )
                    send_telegram_notification(msg)
            
            # 4. Refund
            elif new_sold < prev_sold and prev_available > 0:
                refund_diff = prev_sold - new_sold
                change = {
                    'type': 'refund',
                    'event': event_name,
                    'member': member,
                    'session': session_label,
                    'session_date': adjusted_date,
                    'session_date_display': formatted_date,
                    'refunded_tickets': refund_diff,
                    'old_sold': prev_sold,
                    'new_sold': new_sold,
                    'new_available': new_available,
                    'timestamp': now_wib().isoformat()
                }
                changes.append(change)
                
                msg = (
                    f"💳 *REFUND/CANCEL!*\n\n"
                    f"📅 {formatted_date}\n"
                    f"🎭 {session_label}\n"
                    f"👤 {member}\n\n"
                    f"{refund_diff} transaksi dibatalkan\n"
                    f"Stock: {new_available}"
                )
                send_telegram_notification(msg)
            
            # 5. Sold Out
            if new_available == 0 and prev_available > 0:
                change = {
                    'type': 'sold_out',
                    'event': event_name,
                    'member': member,
                    'session': session_label,
                    'session_date': adjusted_date,
                    'session_date_display': formatted_date,
                    'last_available': prev_available,
                    'timestamp': now_wib().isoformat()
                }
                changes.append(change)
                
                msg = (
                    f"🔴 *SOLD OUT!*\n\n"
                    f"📅 {formatted_date}\n"
                    f"🎭 {session_label}\n"
                    f"👤 {member}\n\n"
                    f"Habis dari {prev_available} tiket!"
                )
                send_telegram_notification(msg)
    
    return changes

def monitor_loop():
    """Main monitoring loop"""
    print("=" * 60)
    print("JKT48 Background Monitor Started")
    print("=" * 60)
    print(f"⏰ Start time: {now_wib().strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print(f"🔄 Refresh interval: {REFRESH_INTERVAL}s")
    print(f"📱 Telegram: Configured")
    print(f"📅 Event date: +1 day offset applied")
    print(f"🌏 Timezone: WIB (UTC+7)")
    print("=" * 60)
    
    iteration = 0
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    while True:
        iteration += 1
        print(f"\n[{now_wib().strftime('%Y-%m-%d %H:%M:%S WIB')}] ⚡ Iteration #{iteration}")
        
        try:
            # Load previous data
            previous_data = load_previous_data()
            change_log = load_change_log()
            
            print(f"  📋 Current log has {len(change_log)} entries")
            
            # Fetch new data
            print(f"  📡 Fetching API...")
            new_data = fetch_api_data()
            
            if new_data:
                print(f"  ✅ Data fetched successfully")
                consecutive_errors = 0
                
                # Detect changes
                if previous_data:
                    changes = detect_changes(previous_data, new_data)
                    
                    if changes:
                        print(f"  🔔 {len(changes)} change(s) detected!")
                        
                        # Append to log
                        change_log.extend(changes)
                        save_change_log(change_log)
                        
                        print(f"  💾 Saved to log (total: {len(change_log)})")
                    else:
                        print(f"  ✓ No changes detected")
                else:
                    print(f"  📝 First run - no previous data to compare")
                
                # Save current as previous
                save_previous_data(new_data)
                
            else:
                print(f"  ❌ Failed to fetch data")
                consecutive_errors += 1
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"  ⚠️  {consecutive_errors} consecutive errors - extended sleep")
                    time.sleep(REFRESH_INTERVAL * 5)
                    consecutive_errors = 0
                    continue
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Keyboard interrupt received")
            print("👋 Shutting down gracefully...")
            break
        
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            consecutive_errors += 1
        
        # Sleep
        print(f"  😴 Sleeping for {REFRESH_INTERVAL}s...")
        time.sleep(REFRESH_INTERVAL)
    
    print("\n" + "=" * 60)
    print("Background Monitor Stopped")
    print(f"Final time: {now_wib().strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print(f"Total iterations: {iteration}")
    print("=" * 60)

if __name__ == "__main__":
    # Create output directory
    os.makedirs("/mnt/user-data/outputs", exist_ok=True)
    
    # Start monitoring
    monitor_loop()
