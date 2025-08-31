from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
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

def click_non_excluded_names(driver, exclude_word="luckytaj"):
    try:
        # Wait for the tag suggestion container
        container = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.xc9l9hb.x10l6tqk.x1lliihq"))
        )

        # Now only look for names inside this container
        name_elements = container.find_elements(By.CSS_SELECTOR, "span._ao3e")

        for elem in name_elements:
            name_text = elem.text.strip()
            print(f"\033[94m[DEBUG]\033[0m Found name element text: '{name_text}'")
            if name_text and exclude_word.lower() not in name_text.lower():
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                    elem.click()
                    print(f"\033[92m[APPROVED]\033[0m Clicked on: {name_text}")
                    return True
                except Exception as e:
                    print(f"\033[91m[WARN]\033[0m Could not click {name_text}: {repr(e)}")
                    continue

        print(f"\033[93m[INFO]\033[0m No names found without '{exclude_word}' inside container")
        return False

    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Could not retrieve names: {repr(e)}")
        return False



def loop_through_numbers():
    """Loop through phone numbers from phone_number.txt and paste into search box"""
    try:
        # Load phone numbers from file
        phone_numbers = []
        with open("phone_number.txt", "r") as f:
            for line in f:
                number = line.strip()
                if number and re.match(r'^\+?\d{10,15}$', number.replace(" ", "").replace("-", "")):
                    phone_numbers.append(number.replace(" ", "").replace("-", ""))
        
        if not phone_numbers:
            print("❌ No valid phone numbers found in phone_number.txt")
            return False
        
        print(f"📞 Loaded {len(phone_numbers)} phone numbers from file")
        
        for number in phone_numbers:
            print(f"🔍 Processing number: {number}")
            
            try:
                # Multiple search box selectors using EC.any_of
                search_selectors = [
                    '[aria-placeholder="Search or start a new chat"]',
                    'div[contenteditable="true"][data-tab="3"]',
                    'div[title="Search input textbox"]',
                    '[data-testid="chat-list-search"]',
                    'div[role="textbox"]'
                ]
                
                try:
                    search_box = WebDriverWait(driver, 10).until(
                        EC.any_of(
                            *[EC.element_to_be_clickable((By.CSS_SELECTOR, selector)) for selector in search_selectors]
                        )
                    )
                    # print(f"✅ Found search box")
                except TimeoutException:
                    print(f"❌ Could not find search box for number {number}")
                    continue

                # Scroll into view and click
                driver.execute_script("arguments[0].scrollIntoView(true);", search_box)
                time.sleep(0.5)
                
                # Click using ActionChains for better reliability
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(driver).move_to_element(search_box).click().perform()
                time.sleep(0.5)
                
                # Copy to clipboard first
                pyperclip.copy(number)
                time.sleep(0.3)
                
                # Clear and paste using ActionChains
                import platform
                actions = ActionChains(driver)
                
                # Focus and clear
                actions.click(search_box)
                if platform.system() == "Darwin":  # macOS
                    actions.key_down(Keys.COMMAND).send_keys("a").key_up(Keys.COMMAND)  # Select all
                    actions.send_keys(Keys.DELETE)  # Delete
                    actions.key_down(Keys.COMMAND).send_keys("v").key_up(Keys.COMMAND)  # Paste
                else:
                    actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL)  # Select all
                    actions.send_keys(Keys.DELETE)  # Delete
                    actions.key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL)  # Paste
                
                actions.perform()
                time.sleep(1)
                
                print(f"\033[92m[APPROVED]\033[0m Pasted number into search: {number}")


                # --- Check for "No chats, contacts or messages found" ---
                try:
                    no_result = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'No chats, contacts or messages found')]"))
                    )
                    if no_result.is_displayed():
                        print(f"\033[91m[WARN]\033[0m No chat found for {number}")
                        # Record the number in not_in_group.txt
                        with open("not_in_group.txt", "a", encoding="utf-8") as f:
                            f.write(f"{number}\n")
                        print(f"\033[93m[RECORDED]\033[0m Number {number} saved to not_in_group.txt")
                        continue  # jump to next number in your loop
                except TimeoutException:
                    # No such span -> safe to continue normal flow
                    pass
                
                # Verify the content was pasted
                time.sleep(0.5)
                current_value = search_box.get_attribute('value') or driver.execute_script("return arguments[0].innerText;", search_box)
                if number not in str(current_value):
                    print(f"⚠️ Paste may have failed, trying direct input...")
                    # Fallback: direct character input
                    search_box.clear()
                    for char in number:
                        search_box.send_keys(char)
                        time.sleep(0.05)
                
                try:
                    # Locate the "Groups in common" div
                    groups_in_common = driver.find_element(
                        By.XPATH, "//div[@role='listitem' and contains(., 'Groups in common')]"
                    )

                    # Get the next sibling div (the chat after it)
                    next_chat = groups_in_common.find_element(By.XPATH, "following-sibling::div[1]")

                    # Click the chat
                    driver.execute_script("arguments[0].scrollIntoView();", next_chat)
                    next_chat.click()
                    print("[INFO] Clicked chat after 'Groups in common'")
                    time.sleep(2)
                    
                    # Send message from file
                    print(f"[INFO] Sending message to chat for number {number}")
                    # test_send_message()
                    send_message_from_file()
                    time.sleep(2)

                except Exception:
                    print(f"\033[91m[WARN]\033[0m 'Groups in common' not found for {number}")
                    # Record the number in not_in_group.txt
                    with open("not_in_group.txt", "a", encoding="utf-8") as f:
                        f.write(f"{number}\n")
                    print(f"\033[93m[RECORDED]\033[0m Number {number} saved to not_in_group.txt")
                    continue

                

                # Wait a bit before next number
                time.sleep(3)

            except Exception as e:
                print(f"⚠️ Could not process number {number}: {repr(e)}")
                continue

    except Exception as e:
        print(f"❌ Error in loop_through_numbers: {repr(e)}")
        return False



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

    time.sleep(1)
    message_input.send_keys("@")
    time.sleep(0.5)
    click_non_excluded_names(driver)

    time.sleep(2)
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

        # --- Click to open tag suggestions and select non-excluded name ---
        message_input.send_keys("@")
        time.sleep(0.5)
        click_non_excluded_names(driver)
        time.sleep(0.5)

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

    # Pause here to allow user adjust position
    time.sleep(2)
    loop_through_numbers()    
    # loop_through_all_chats_with_scroll()

except:
    print("WhatsApp Web header not found - already logged in")
    # Click the Groups filter button
    time.sleep(2)
    loop_through_numbers()
    # loop_through_all_chats_with_scroll()

# Wait for WhatsApp to load completely
WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div._ak72"))
)





