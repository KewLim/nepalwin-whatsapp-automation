from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import os
import glob
from selenium.webdriver.support.ui import Select
from datetime import datetime
from collections import defaultdict
from tqdm import tqdm
import pyperclip
import re
import signal
import sys
import threading

# Global control variables
script_paused = False
script_stopped = False
pause_lock = threading.Lock()

def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) for graceful shutdown"""
    global script_stopped
    print("\n🛑 Script interrupted by user - Exiting gracefully...")
    script_stopped = True
    try:
        driver.quit()
    except:
        pass
    sys.exit(0)

def pause_script():
    """Pause the script execution"""
    global script_paused
    with pause_lock:
        script_paused = True
        print("\n🔄 SCRIPT PAUSED - Type 'resume' and press ENTER to continue, or 'stop' to exit:")
        
        while script_paused:
            try:
                user_input = input().strip().lower()
                if user_input == 'resume':
                    script_paused = False
                    print("▶️ SCRIPT RESUMED")
                elif user_input == 'stop':
                    print("🛑 SCRIPT STOPPED by user")
                    driver.quit()
                    sys.exit(0)
                else:
                    print("Type 'resume' to continue or 'stop' to exit:")
            except KeyboardInterrupt:
                signal_handler(None, None)

def check_script_control():
    """Check if script should pause or stop"""
    global script_paused, script_stopped
    
    if script_stopped:
        print("Script stopped by user")
        try:
            driver.quit()
        except:
            pass
        sys.exit(0)

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, signal_handler)
    print("🎮 Controls: Ctrl+C = Stop | Type 'PAUSE' in terminal during execution to pause")

def wait_for_user_input(message="Press ENTER to continue..."):
    """Pause execution until user presses ENTER in terminal"""
    try:
        input(message)
        print("Continuing...")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return False
    return True

def click_group_filter():
    """Click on the Groups filter button"""
    try:
        group_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "group-filter"))
        )
        group_button.click()
        print("Groups filter button clicked successfully")
        return True
    except Exception as e:
        print(f"Failed to click Groups filter button: {e}")
        return False

def loop_through_chats():
    """Loop through all chats sequentially infinitely (no batch)"""
    try:
        # Wait for WhatsApp to load completely
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div._ak72"))
        )
        time.sleep(3)

        # Possible selectors
        selectors = [
            'div._ak72',
            'div[role="none"][tabindex="0"]',
            'div._ak72.false.false._ak73._asiw._ap1-._ap1_',
            'div[role="gridcell"]',
            'div[tabindex="0"] div._ak72'
        ]

        total_processed = 0
        last_processed_chat_name = None

        while True:
            # Locate chats
            chat_items = []
            for selector in selectors:
                chat_items = driver.find_elements(By.CSS_SELECTOR, selector)
                if len(chat_items) > 0:
                    print(f"✅ Using selector '{selector}', found {len(chat_items)} chats")
                    break

            if len(chat_items) == 0:
                print("❌ No chat items found - retrying in 3 seconds...")
                time.sleep(3)
                continue

            # Iterate through chats
            found_next_chat = False
            for i, chat in enumerate(chat_items):
                try:
                    # Pause/stop controls
                    check_script_control()

                    # Get chat name
                    current_chat_name = get_chat_name(chat)
                    if last_processed_chat_name and current_chat_name == last_processed_chat_name:
                        # Already processed last chat, skip
                        continue

                    # Scroll into view
                    driver.execute_script("arguments[0].scrollIntoView();", chat)
                    time.sleep(0.5)

                    # Click chat
                    chat.click()
                    total_processed += 1
                    print(f"\033[1;32m✅ Successfully clicked on chat: {current_chat_name}\033[0m")
                    last_processed_chat_name = current_chat_name
                    found_next_chat = True

                    # Wait for chat to load
                    time.sleep(1.5)

                    # Check if chat group is available
                    group_unavailable = check_group_availability()

                    # Predict next chat name
                    next_chat_name = None
                    if i + 1 < len(chat_items):
                        try:
                            next_chat_name = get_chat_name(chat_items[i + 1])
                        except:
                            next_chat_name = None

                    # Send message if allowed
                    if not group_unavailable and next_chat_name:
                        saved_position = get_current_scroll_position()
                        print(f" DEBUG - Saved position: {saved_position}")
                        test_send_message()
                        time.sleep(1)
                        scroll_to_top()
                        time.sleep(1)
                        detect_chat_list_scrollbar(saved_position, next_chat_name)
                    elif not next_chat_name:
                        print(f"Last Chat: {current_chat_name} - no message sent")
                    else:
                        print("Skipping message send - group is not available")

                    # Small delay before next iteration
                    time.sleep(1)

                except Exception as e:
                    print(f"⚠️ Error on chat #{total_processed}: {e}")
                    continue

            if not found_next_chat:
                # Scroll down to load more chats if no new chat was processed
                print("🔄 Scrolling to load more chats...")
                driver.execute_script("document.querySelector('div._ak72').scrollIntoView(false);")
                time.sleep(2)

    except Exception as e:
        print(f"❌ Error in loop_through_chats: {e}")
        return False





def find_first_visible_chat_and_next():
    """Find the first visible chat and next chat name simultaneously"""
    try:
        selectors = [
            'div._ak72',
            'div[role="listitem"]',
            'div[data-testid="chat-list-item"]',
            'div[role="gridcell"]',
            'div[tabindex="0"] div._ak72'
        ]
        
        for selector in selectors:
            try:
                chat_items = driver.find_elements(By.CSS_SELECTOR, selector)
                if len(chat_items) >= 1:
                    current_chat = chat_items[0]
                    
                    # Get next chat name if there are at least 2 chats
                    next_chat_name = None
                    if len(chat_items) >= 2:
                        next_chat = chat_items[1]
                        next_chat_name = get_chat_name(next_chat)
                    
                    return current_chat, next_chat_name
            except Exception as e:
                continue
        
        return None, None
    except Exception as e:
        print(f"❌ Error finding first visible chat and next: {e}")
        return None, None

def get_current_chat_name():
    """Get the name of the currently opened chat"""
    try:
        # Look for chat name in the chat header
        chat_name_selectors = [
            'span[title]',
            'div[title]', 
            'span[dir="auto"]',
            '[data-testid="conversation-info-header-chat-title"]'
        ]
        
        for selector in chat_name_selectors:
            try:
                name_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in name_elements:
                    name = element.get_attribute('title') or element.text.strip()
                    if name and len(name) < 100:  # Reasonable chat name length
                        return name
            except:
                continue
        
        return "Unknown Chat"
        
    except Exception as e:
        print(f"❌ Error getting current chat name: {e}")
        return "Unknown Chat"

def find_next_chat_name():
    """Find the name of the next chat in the list"""
    try:
        # Get all visible chats
        selectors = [
            'div._ak72',
            'div[role="listitem"]',
            'div[data-testid="chat-list-item"]',
            'div[role="gridcell"]',
            'div[tabindex="0"] div._ak72'
        ]
        
        for selector in selectors:
            try:
                chat_items = driver.find_elements(By.CSS_SELECTOR, selector)
                if len(chat_items) >= 2:  # Need at least 2 chats to find the next one
                    next_chat = chat_items[1]  # Second chat is the "next" one
                    next_chat_name = get_chat_name(next_chat)
                    return next_chat_name
            except Exception as e:
                continue
        
        return None  # No next chat found
        
    except Exception as e:
        print(f"❌ Error finding next chat name: {e}")
        return None

def get_current_scroll_position():
    """Get current scrollbar position and return coordinates"""
    try:
        # Find the pane-side container
        container = driver.find_element(By.CSS_SELECTOR, '#pane-side')
        
        # Get scroll information
        scroll_top = driver.execute_script("return arguments[0].scrollTop;", container)
        scroll_height = driver.execute_script("return arguments[0].scrollHeight;", container)
        client_height = driver.execute_script("return arguments[0].clientHeight;", container)
        
        # Calculate scroll percentage
        max_scroll = scroll_height - client_height
        scroll_percentage = (scroll_top / max_scroll * 100) if max_scroll > 0 else 0
        
        position_info = {
            'scroll_top': scroll_top,
            'scroll_height': scroll_height,
            'client_height': client_height,
            'max_scroll': max_scroll,
            'scroll_percentage': scroll_percentage
        }
        
        print(f"📍 Current scroll position: {scroll_top}px (\033[92m{scroll_percentage:.1f}%\033[0m)")
        return position_info
        
    except Exception as e:
        print(f"❌ Error getting scroll position: {e}")
        return None

def detect_chat_list_scrollbar(target_position=None, next_chat_to_click=None):
    """Detect WhatsApp Web chat list scrollbar and move to target position"""
    try:
        # Try different selectors one by one to debug - including pane-side
        selectors = [
            '#pane-side',
            '[data-testid="chat-list"]',
            'div[role="grid"]', 
            'div[tabindex="0"]',
            'div._ak72',
            'div[aria-label*="Chat list"]'
        ]
        
        found_container = None
        for selector in selectors:
            try:
                containers = driver.find_elements(By.CSS_SELECTOR, selector)
                # print(f"🔍 Selector '{selector}': Found {len(containers)} elements")
                
                for i, container in enumerate(containers):
                    scroll_height = driver.execute_script("return arguments[0].scrollHeight;", container)
                    client_height = driver.execute_script("return arguments[0].clientHeight;", container)
                    print(f"   Container {i+1}: Height={client_height}px, ScrollHeight={scroll_height}px")
                    
                    if scroll_height > client_height:
                        # print(f"✅ Found scrollable container using '{selector}' (container {i+1})")
                        found_container = container
                        break
                        
                if found_container:
                    break
                    
            except Exception as e:
                print(f"❌ Error with selector '{selector}': {e}")
                continue
        
        if not found_container:
            print("❌ No scrollable chat list container found")
            return False
        
        # If target_position is provided, move to that position
        if target_position:
            target_scroll = target_position.get('scroll_top', 0)
            print(f"[INFO] Moving to target position: {target_scroll}px")
            driver.execute_script(f"arguments[0].scrollTop = {target_scroll};", found_container)
            time.sleep(1)
            new_position = driver.execute_script("return arguments[0].scrollTop;", found_container)
            print(f"[APPROVED] Moved to position: {new_position}px")
            
            # If next_chat_to_click is provided, find and click that chat
            if next_chat_to_click:
                # print(f"🔍 Looking for chat: {next_chat_to_click}")
                chat_found = click_chat_by_name(next_chat_to_click)
                if chat_found:
                    print(f"\033[1;33m✅ Successfully clicked on chat: {next_chat_to_click}\033[0m")
                    test_send_message()
                    
                    # Wait for WhatsApp to switch to the new chat and verify
                    time.sleep(2)
                    actual_chat_name = get_current_chat_name()
                    print(f"🔍 Verification - Current chat is now: {actual_chat_name}")
                    
                    # Don't send message here - let the main loop handle it
                else:
                    print(f"❌ Could not find chat: {next_chat_to_click}")
            
            return True
        else:
            print("✅ Chat list scrollbar detected, returning container info")
            return {'container': found_container}
        
    except Exception as e:
        print(f"❌ Error detecting chat list scrollbar: {e}")
        return False

def get_chat_name(chat_element):
    """Extract chat name from a chat element"""
    try:
        # Try different selectors to get chat name
        name_selectors = [
            'span[title]',
            'span._ak8o',
            'span[dir="auto"]',
            'div[title]'
        ]
        
        for selector in name_selectors:
            try:
                name_element = chat_element.find_element(By.CSS_SELECTOR, selector)
                name = name_element.get_attribute('title') or name_element.text.strip()
                if name:
                    return name
            except:
                continue
        
        # Fallback: get text content
        return chat_element.text.strip().split('\n')[0]
        
    except Exception as e:
        return f"Unknown_{str(e)[:10]}"

def click_chat_by_name(chat_name):
    """Find and click a chat by its name"""
    try:
        # Chat selectors to find chat items
        chat_selectors = [
            'div[role="listitem"]',
            'div._ak72',
            'div[data-testid="chat-list-item"]',
            'div[role="gridcell"]',
            'div[tabindex="0"] div._ak72'
        ]
        
        # Name selectors to find chat names within chat items
        chat_name_selectors = [
            'span[title]',
            'div[title]',
            'span[dir="auto"]',
            '[data-testid="conversation-info-header-chat-title"]'
        ]
        
        for selector in chat_selectors:
            try:
                chat_items = driver.find_elements(By.CSS_SELECTOR, selector)
                # print(f"🔍 Found {len(chat_items)} chats with selector: {selector}")
                
                for chat in chat_items:
                    try:
                        # Try to find chat name using specific name selectors
                        chat_name_found = None
                        for name_selector in chat_name_selectors:
                            try:
                                name_element = chat.find_element(By.CSS_SELECTOR, name_selector)
                                chat_name_found = name_element.get_attribute('title') or name_element.text.strip()
                                if chat_name_found:
                                    break
                            except:
                                continue
                        
                        # If no specific name found, use full text as fallback
                        if not chat_name_found:
                            chat_name_found = chat.text.strip()
                        
                        # Check if this is the chat we're looking for
                        if chat_name and chat_name_found and chat_name.lower() in chat_name_found.lower():
                            # print(f"✅ Found matching chat: {chat_name_found[:50]}...")
                            # Scroll the chat into view first
                            driver.execute_script("arguments[0].scrollIntoView();", chat)
                            time.sleep(0.5)
                            chat.click()
                            return True
                            
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"❌ Error with selector {selector}: {e}")
                continue
        
        print(f"❌ Chat '{chat_name}' not found in current visible chats")
        return False
        
    except Exception as e:
        print(f"❌ Error finding chat by name: {e}")
        return False

def scroll_to_top():
    """Scroll to the top of the WhatsApp chat list"""
    try:
        container = driver.find_element(By.CSS_SELECTOR, '#pane-side')
        driver.execute_script("arguments[0].scrollTop = 0;", container)
        print("🔝 Scrolled to top of chat list")
        return True
    except Exception as e:
        print(f"❌ Error scrolling to top: {e}")
        return False


def check_group_availability():
    """Check if group is no longer available and handle accordingly"""
    try:
        # Check for "This group is no longer available" message
        unavailable_message = driver.find_elements(By.XPATH, "//h1[contains(text(), 'This group is no longer available')]")
        
        if len(unavailable_message) > 0:
            print("\033[91mGroup is no longer available - looking for 'See group' button\033[0m")
            # Look for "See group" button and click it
            see_group_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'See group')]"))
            )
            see_group_button.click()
            print("Clicked 'See group' button")
            time.sleep(2)  # Wait for action to complete
            return True
        
        # Check for "You can't send messages to this group because you're no longer a member" message
        no_member_message = driver.find_elements(By.XPATH, "//div[contains(text(), \"You can't send messages to this group because you're no longer a member\")]")
        
        if len(no_member_message) > 0:
            print("\033[91mYou're no longer a member of this group - skipping to next chat\033[0m")
            return True  # Return True to skip sending message
        
        # Group is available, continue normally
        return False
            
    except Exception as e:
        print(f"Error checking group availability: {e}")
        return False

def test_send_message():
    """Test function to verify messaging functionality"""
    # --- Locate message input ---
    selectors = [
        (By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="10"]'),
        (By.CSS_SELECTOR, 'div[contenteditable="true"]'),
        (By.CSS_SELECTOR, 'p.selectable-text.copyable-text'),
        (By.CSS_SELECTOR, '[data-testid="conversation-compose-box-input"]')
    ]
    message_input = WebDriverWait(driver, 10).until(
        EC.any_of(*[EC.element_to_be_clickable(sel) for sel in selectors])
    )
    
    # Click and clear the message input
    message_input.click()
    time.sleep(0.5)
    # Select all text and delete
    message_input.send_keys(Keys.COMMAND, 'a')  # Select all (macOS)
    message_input.send_keys(Keys.DELETE)  # Clear selected text
    print("Message input cleared")
    return True

def send_message_from_file(message_index=0):
    """Parse and send message content from description.txt file and attach an image from IMAGE-TO-SEND folder"""
    import os, glob, time, pyperclip
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        # --- Load messages ---
        messages = load_message_from_file()
        if not messages:
            return False

        if message_index >= len(messages):
            message_index = 0

        message = messages[message_index]
        message_content = message.get('content', '')
        if not message_content:
            print("Selected message is empty - skipping")
            return False

        print(f"📤 Sending message ({message['type']}): {message_content[:50]}...")

        # --- Locate message input ---
        selectors = [
            (By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="10"]'),
            (By.CSS_SELECTOR, 'div[contenteditable="true"]'),
            (By.CSS_SELECTOR, 'p.selectable-text.copyable-text'),
            (By.CSS_SELECTOR, '[data-testid="conversation-compose-box-input"]')
        ]
        message_input = WebDriverWait(driver, 10).until(
            EC.any_of(*[EC.element_to_be_clickable(sel) for sel in selectors])
        )

        # Click and clear the message input
        message_input.click()
        time.sleep(0.5)
        # Select all text and delete
        message_input.send_keys(Keys.COMMAND, 'a')  # Select all (macOS)
        message_input.send_keys(Keys.DELETE)  # Clear selected text
        print("Message input cleared")
        time.sleep(1)

        # --- Paste text into input ---
        pyperclip.copy(message_content)
        message_input.click()
        message_input.send_keys(Keys.COMMAND, 'v')  # macOS paste
        print(f"[INFO] Text pasted: {message_content[:50]}...")
        time.sleep(1)

        # --- Check for image in IMAGE-TO-SEND folder ---
        image_folder = "IMAGE-TO-SEND"
        image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp"]
        image_path = None
        for ext in image_extensions:
            files = glob.glob(os.path.join(image_folder, ext))
            if files:
                image_path = os.path.abspath(files[0])
                break

        if image_path:
            print(f"[INFO] Found image: {image_path}")
            
            # Use system clipboard method to attach image
            import subprocess
            try:
                # Copy image to clipboard using osascript (macOS)
                subprocess.run([
                    'osascript', '-e',
                    f'set the clipboard to (read file POSIX file "{image_path}" as JPEG picture)'
                ], check=True)
                
                # Click message input and paste
                message_input.click()
                time.sleep(0.5)
                
                # Paste the image
                message_input.send_keys(Keys.COMMAND, 'v')
                time.sleep(2)
                
                print(f"[INFO] Image pasted from clipboard: {os.path.basename(image_path)}")
                time.sleep(1)
                # Send the message using Enter key
                # wait for the button to be clickable
                send_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[@role="button" and @aria-label="Send"]'))
                )

                send_button.click()
                print("[INFO] Message + image sent successfully!")
                time.sleep(3)
                
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Failed to copy image to clipboard: {e}")
                print("[INFO] Sending text message only")
        else:
            # No image found, just send text
            print("[INFO] Text message sent successfully!")

        return True
    
    
    except FileNotFoundError:
        print("description.txt file not found")
        return False
    except Exception as e:
        print(f"Error sending message: {e}")
        return False
    

    time.sleep(2)  # Wait a bit before next action



def load_message_from_file():
    """Load and parse message content from description.txt file"""
    try:
        filename = "description.txt"
        
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read().strip()
        
        if not content:
            print("⚠️ description.txt is empty")
            return None
            
        # Parse different message formats
        messages = []
        
        # Format 1: Simple text (entire file is one message)
        if not any(marker in content for marker in ['---', '###', '#MESSAGE']):
            messages.append({
                "content": content,
                "type": "simple"
            })
            print(f"📄 Loaded simple message ({len(content)} characters)")
            
        # Format 2: Multiple messages separated by ---
        elif '---' in content:
            parts = [part.strip() for part in content.split('---') if part.strip()]
            for i, part in enumerate(parts):
                messages.append({
                    "content": part,
                    "type": "multi",
                    "index": i + 1
                })
            print(f"📄 Loaded {len(messages)} messages separated by '---'")
            
        # Format 3: Numbered messages with #MESSAGE pattern
        elif '#MESSAGE' in content.upper():
            pattern = re.compile(r"#MESSAGE\s*(\d+)\s*[:-]\s*(.*?)(?=#MESSAGE|\Z)", re.DOTALL | re.IGNORECASE)
            matches = pattern.findall(content)
            for num, msg_content in matches:
                messages.append({
                    "content": msg_content.strip(),
                    "type": "numbered",
                    "number": int(num)
                })
            print(f"📄 Loaded {len(messages)} numbered messages")
            
        if not messages:
            print("⚠️ Could not parse message format, using entire content as single message")
            messages.append({
                "content": content,
                "type": "fallback"
            })
            
        return messages
        
    except FileNotFoundError:
        print("❌ description.txt file not found")
        return None
    except Exception as e:
        print(f"❌ Error loading message file: {e}")
        return None




# ============= Main Script =============


profile_path = "/Users/admin/Library/Application Support/Firefox/Profiles/7oz304au.default-release"

options = Options()
options.profile = webdriver.FirefoxProfile(profile_path)

# Anti-detection measures
options.set_preference("dom.webdriver.enabled", False)
options.set_preference("useAutomationExtension", False)
options.set_preference("general.useragent.override", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0")

# Headless mode if needed
# options.add_argument('--headless')

# Setup the driver
service = Service(GeckoDriverManager().install())
driver = webdriver.Firefox(service=service, options=options)
driver.maximize_window()

# Setup signal handlers for pause/stop controls
setup_signal_handlers()

driver.get("https://web.whatsapp.com/")

# Wait and check if login is required
try:
    # Check if WhatsApp Web header is present (means not logged in)
    login_header = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'x3nfvp2')]//h1[text()='WhatsApp Web']"))
    )
    # Click the Groups filter button
    click_group_filter()
    # Pause here to allow user adjust position
    wait_for_user_input("Adjust your position if needed, then press ENTER to continue...")
    time.sleep(2)
    loop_through_chats()    
    # loop_through_all_chats_with_scroll()

except:
    print("WhatsApp Web header not found - already logged in")
    # Click the Groups filter button
    click_group_filter()
    time.sleep(2)
    loop_through_chats()
    # loop_through_all_chats_with_scroll()

# Wait for WhatsApp to load completely
WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div._ak72"))
)





