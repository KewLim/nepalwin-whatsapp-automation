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

def loop_through_chats_batched():
    """Loop through all chats using batch processing - keeps current fast search but handles 100+ chats"""
    try:
        # Wait for WhatsApp to load completely - using a more general selector
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div._ak72"))
        )
        
        # Add some extra wait time for elements to fully load
        time.sleep(3)
        
        # Try multiple selectors based on your actual WhatsApp structure
        selectors = [
            'div._ak72',  # Based on your HTML structure
            'div[role="none"][tabindex="0"]',  # The outer container from your HTML
            'div._ak72.false.false._ak73._asiw._ap1-._ap1_',  # Full class from your HTML
            'div[role="gridcell"]',  # Another element from your structure
            'div[tabindex="0"] div._ak72'  # Combination selector
        ]
        
        total_processed = 0
        batch_count = 0
        max_batches = 20  # Prevent infinite loop
        last_chat_name = None  # Track the last processed chat name
        
        while batch_count < max_batches:
            batch_count += 1
            print(f"\n=== Processing Batch #{batch_count} ===")
            
            # Find current visible chats (same fast method as before)
            chat_items = []
            for selector in tqdm(selectors, desc="Trying selectors"):
                chat_items = driver.find_elements(By.CSS_SELECTOR, selector)
                tqdm.write(f"Selector '{selector}': Found {len(chat_items)} elements")
                if len(chat_items) > 0:
                    break
            
            if len(chat_items) == 0:
                print("No chat items found in this batch - ending search")
                break
            
            print(f"Found {len(chat_items)} chats in batch #{batch_count}")
            
            # Process current batch of chats
            processed_in_batch = 0
            start_processing = (last_chat_name is None)  # Start processing if no last chat name yet
            
            for i, chat in enumerate(chat_items):
                try:
                    # Check pause/stop controls
                    check_script_control()
                    
                    # Get current chat name to check if we should start processing
                    if not start_processing:
                        try:
                            # Get chat name using same logic as the last chat detection
                            current_chat_name = None
                            chat_name_selectors = [
                                'span[title]',
                                'div[title]',
                                'span[dir="auto"]',
                                '[data-testid="conversation-info-header-chat-title"]'
                            ]
                            
                            for selector in chat_name_selectors:
                                try:
                                    name_element = chat.find_element(By.CSS_SELECTOR, selector)
                                    potential_name = name_element.get_attribute("title") or name_element.text
                                    if potential_name and len(potential_name) < 100:
                                        current_chat_name = potential_name
                                        break
                                except:
                                    continue
                            
                            if not current_chat_name:
                                full_text = chat.text
                                current_chat_name = full_text.split('\n')[0] if full_text else "Unknown"
                            
                            # Check if this is the last processed chat or after it
                            if current_chat_name == last_chat_name:
                                print(f"Found last processed chat: {current_chat_name} - Starting from here")
                                start_processing = True
                            else:
                                print(f"Skipping already processed chat: {current_chat_name}")
                                continue
                                
                        except:
                            # If we can't get name, skip this chat
                            print(f"Skipping chat {i+1} - couldn't get name")
                            continue
                    
                    # Scroll into view just in case
                    driver.execute_script("arguments[0].scrollIntoView();", chat)
                    time.sleep(0.5)
                    
                    # Click the chat
                    chat.click()
                    total_processed += 1
                    processed_in_batch += 1
                    
                    # Check if this is the last chat in current batch
                    is_last_chat = (i + 1) == len(chat_items)
                    
                    if is_last_chat:
                        print(f"\033[1;33mProcessed chat #{total_processed} (Batch {batch_count}, Item {i+1}) - Last Chat\033[0m")
                    else:
                        print(f"\033[1;33mProcessed chat #{total_processed} (Batch {batch_count}, Item {i+1})\033[0m")
                    
                    time.sleep(1.5)  # Give time for chat to load
                    
                    # check if chat group is no longer available
                    group_unavailable = check_group_availability()
                    
                    # Send message only if group is available and not last chat
                    if not group_unavailable and not is_last_chat:
                        test_send_message()
                    elif is_last_chat:
                        # Get chat name dynamically - find the chat title/name element within the chat
                        try:
                            # Try different selectors to find just the chat name
                            chat_name_selectors = [
                                'span[title]',  # Chat name with title attribute
                                'div[title]',   # Alternative title container
                                'span[dir="auto"]',  # Chat name span
                                '[data-testid="conversation-info-header-chat-title"]'  # Specific chat title
                            ]
                            
                            chat_name = None
                            for selector in chat_name_selectors:
                                try:
                                    name_element = chat.find_element(By.CSS_SELECTOR, selector)
                                    potential_name = name_element.get_attribute("title") or name_element.text
                                    # Only use if it's a reasonable length for a chat name (not a full message)
                                    if potential_name and len(potential_name) < 100:
                                        chat_name = potential_name
                                        break
                                except:
                                    continue
                            
                            if not chat_name:
                                # Fallback: try to extract first line of text content
                                full_text = chat.text
                                chat_name = full_text.split('\n')[0] if full_text else "Unknown"
                                
                            print(f"Last Chat: {chat_name}")
                            last_chat_name = chat_name
                        except:
                            print("Last Chat: Unknown")
                        time.sleep(5)
                        # Continue to next batch - don't call test_send_message()
                        continue
                    else:
                        print("Skipping message send - group is not available")
                    
                except Exception as e:
                    print(f"Error on chat #{total_processed}: {e}")
                    
            print(f"Batch #{batch_count} completed - processed {processed_in_batch} chats")
            
            # Quick pause before searching for next batch
            time.sleep(1)
            print("Searching for next batch of chats...")
            time.sleep(4)
                
        print(f"\n=== SUMMARY ===")
        print(f"Total batches processed: {batch_count}")
        print(f"Total chats processed: {total_processed}")
        print("Finished processing all available chats")
        return True
        
    except Exception as e:
        print(f"Error in loop_through_chats_batched: {e}")
        return False

def loop_through_chats():
    """Loop through all chats in the chat list and click on each one"""
    try:
        # Wait for WhatsApp to load completely - using a more general selector
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div._ak72"))
        )
        
        # Add some extra wait time for elements to fully load
        time.sleep(3)
        
        # Try multiple selectors based on your actual WhatsApp structure
        selectors = [
            'div._ak72',  # Based on your HTML structure
            'div[role="none"][tabindex="0"]',  # The outer container from your HTML
            'div._ak72.false.false._ak73._asiw._ap1-._ap1_',  # Full class from your HTML
            'div[role="gridcell"]',  # Another element from your structure
            'div[tabindex="0"] div._ak72'  # Combination selector
        ]
        
        chat_items = []
        for selector in tqdm(selectors, desc="Trying selectors"):
            chat_items = driver.find_elements(By.CSS_SELECTOR, selector)
            tqdm.write(f"Selector '{selector}': Found {len(chat_items)} elements")
            if len(chat_items) > 0:
                break
        
        if len(chat_items) == 0:
            print("No chat items found. Checking page source...")
            # Debug: Check if we're on the right page
            if "WhatsApp" in driver.title:
                print("On WhatsApp page, but no chats found")
            else:
                print(f"Current page title: {driver.title}")
            return False
        
        print(f"Found {len(chat_items)} chats")
        
        for i, chat in enumerate(chat_items):
            try:
                # Scroll into view just in case
                driver.execute_script("arguments[0].scrollIntoView();", chat)
                time.sleep(0.5)
                
                # Click the chat
                chat.click()
                print(f"\033[1;33mClicked chat #{i+1}\033[0m")
                time.sleep(1.5)  # Give time for chat to load
                
                # check if chat group is no longer available
                group_unavailable = check_group_availability()
                
                # Send message only if group is available
                if not group_unavailable:
                    # send_message_from_file()
                    test_send_message()
                else:
                    print("Skipping message send - group is not available")
                
            except Exception as e:
                print(f"Error on chat #{i+1}: {e}")
                
        print("Finished looping through all chats")
        return True
        
    except Exception as e:
        print(f"Error in loop_through_chats: {e}")
        return False

def loop_through_all_chats_with_scroll():
    """Loop through ALL chats using scroll-and-collect approach to handle 100+ chats"""
    try:
        # Wait for WhatsApp to load completely
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div._ak72"))
        )
        
        time.sleep(3)
        
        # Find the chat list container for scrolling
        chat_list_container = None
        container_selectors = [
            '[data-testid="chat-list"]',
            'div[role="grid"]',
            'div[tabindex="0"]',  # Main scrollable container
            'div._ak72'  # Fallback to individual chat selector's parent
        ]
        
        for selector in container_selectors:
            try:
                chat_list_container = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"Found chat list container using selector: {selector}")
                break
            except:
                continue
        
        if not chat_list_container:
            print("Could not find chat list container, falling back to page scroll")
            chat_list_container = driver.find_element(By.TAG_NAME, "body")
        
        # Chat selectors (same as original function)
        chat_selectors = [
            'div._ak72',
            'div[role="none"][tabindex="0"]',
            'div._ak72.false.false._ak73._asiw._ap1-._ap1_',
            'div[role="gridcell"]',
            'div[tabindex="0"] div._ak72'
        ]
        
        processed_chats = set()  # Track processed chats by their text content
        all_chats = []
        last_chat_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 50  # Prevent infinite scrolling
        
        print("Starting scroll-and-collect approach...")
        
        while scroll_attempts < max_scroll_attempts:
            # Collect current visible chats
            current_chats = []
            for selector in chat_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        current_chats = elements
                        break
                except:
                    continue
            
            # Process new chats (avoid duplicates)
            new_chats_found = 0
            for chat in current_chats:
                try:
                    # Use chat text or other identifier to avoid duplicates
                    chat_identifier = chat.get_attribute('innerHTML')[:100]  # First 100 chars as ID
                    if chat_identifier and chat_identifier not in processed_chats:
                        processed_chats.add(chat_identifier)
                        all_chats.append(chat)
                        new_chats_found += 1
                except:
                    continue
            
            current_total = len(all_chats)
            print(f"Scroll attempt {scroll_attempts + 1}: Found {new_chats_found} new chats, Total: {current_total}")
            
            # Check if we found new chats
            if current_total == last_chat_count:
                # No new chats found, try scrolling a bit more
                if scroll_attempts < 3:  # Give it a few more tries
                    scroll_attempts += 1
                    time.sleep(1)
                else:
                    print("No new chats found after scrolling, assuming we've reached the end")
                    break
            else:
                last_chat_count = current_total
                scroll_attempts = 0  # Reset scroll attempts when we find new chats
            
            # Scroll down to load more chats
            try:
                # Scroll the chat list container
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", chat_list_container)
                time.sleep(2)  # Wait for new chats to load
                
                # Alternative scroll method if the first doesn't work
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
            except Exception as e:
                print(f"Error during scrolling: {e}")
                break
            
            scroll_attempts += 1
        
        print(f"Scroll collection complete! Found {len(all_chats)} total chats")
        
        if len(all_chats) == 0:
            print("No chats found even after scrolling")
            return False
        
        # Now process all collected chats
        for i, chat in enumerate(tqdm(all_chats, desc="Processing chats")):
            try:
                # Scroll chat into view
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", chat)
                time.sleep(0.5)
                
                # Click the chat
                chat.click()
                print(f"\033[1;33mProcessing chat #{i+1}/{len(all_chats)}\033[0m")
                time.sleep(1.5)
                
                # Check if chat group is available
                group_unavailable = check_group_availability()
                
                # Send message only if group is available
                if not group_unavailable:
                    # send_message_from_file()
                    test_send_message()
                else:
                    print("Skipping message send - group is not available")
                    
            except Exception as e:
                print(f"Error processing chat #{i+1}: {e}")
                continue
        
        print(f"Finished processing all {len(all_chats)} chats")
        return True
        
    except Exception as e:
        print(f"Error in loop_through_all_chats_with_scroll: {e}")
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
    print("TEST HERE")
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
                time.sleep(1)
                
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
    loop_through_chats_batched()    
    # loop_through_all_chats_with_scroll()

except:
    print("WhatsApp Web header not found - already logged in")
    # Click the Groups filter button
    click_group_filter()
    time.sleep(2)
    loop_through_chats_batched()
    # loop_through_all_chats_with_scroll()

# Wait for WhatsApp to load completely
WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div._ak72"))
)





