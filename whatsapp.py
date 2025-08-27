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
                    send_message_from_file()
                else:
                    print("Skipping message send - group is not available")
                
            except Exception as e:
                print(f"Error on chat #{i+1}: {e}")
                
        print("Finished looping through all chats")
        return True
        
    except Exception as e:
        print(f"Error in loop_through_chats: {e}")
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
                
                # Wait for send button and click
                send_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'span[data-icon="send"]'))
                )
                # send_btn.click()
                print("[INFO] Message + image sent successfully!")
                
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



driver.get("https://web.whatsapp.com/")

# Wait and check if login is required
try:
    # Check if WhatsApp Web header is present (means not logged in)
    login_header = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'x3nfvp2')]//h1[text()='WhatsApp Web']"))
    )
    # Click the Groups filter button
    click_group_filter()
    time.sleep(2)
    loop_through_chats()    

except:
    print("WhatsApp Web header not found - already logged in")
    # Click the Groups filter button
    click_group_filter()
    time.sleep(2)
    loop_through_chats()

# Wait for WhatsApp to load completely
WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div._ak72"))
)





