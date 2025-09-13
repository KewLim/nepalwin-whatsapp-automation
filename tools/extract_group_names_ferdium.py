#!/usr/bin/env python3
"""
WhatsApp Group Name Extractor for Ferdium
Extracts all group chat names from WhatsApp Web running inside Ferdium
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import os
import re
from datetime import datetime
import subprocess

def find_ferdium_debug_port():
    """Find Ferdium process and get its debug port"""
    try:
        # Look for Ferdium process
        result = subprocess.run(['pgrep', '-f', 'Ferdium'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Ferdium process found")
            return True
        else:
            print("❌ Ferdium process not found")
            return False
    except Exception as e:
        print(f"❌ Error checking Ferdium process: {e}")
        return False

def setup_ferdium_driver():
    """Setup Chrome WebDriver to connect to Ferdium"""
    print("🔧 Setting up Chrome WebDriver to connect to Ferdium...")
    
    try:
        # Chrome options for connecting to existing instance
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Create driver
        driver = webdriver.Chrome(options=chrome_options)
        
        print("✅ Successfully connected to Ferdium")
        return driver
        
    except Exception as e:
        print(f"❌ Error connecting to Ferdium: {e}")
        print("\n💡 To fix this:")
        print("1. Close Ferdium completely")
        print("2. Start Ferdium with remote debugging:")
        print("   /Applications/Ferdium.app/Contents/MacOS/Ferdium --remote-debugging-port=9222")
        print("3. Open WhatsApp service in Ferdium")
        print("4. Run this script again")
        return None

def find_whatsapp_tab(driver):
    """Find and switch to WhatsApp tab in Ferdium"""
    try:
        print("🔍 Looking for WhatsApp tab...")
        
        # Get all window handles
        handles = driver.window_handles
        print(f"Found {len(handles)} tabs/windows")
        
        whatsapp_handle = None
        for handle in handles:
            driver.switch_to.window(handle)
            current_url = driver.current_url
            current_title = driver.title
            
            print(f"Checking tab: {current_title} - {current_url}")
            
            # Check if this is WhatsApp Web
            if "web.whatsapp.com" in current_url or "whatsapp" in current_title.lower():
                whatsapp_handle = handle
                print(f"✅ Found WhatsApp tab: {current_title}")
                break
        
        if whatsapp_handle:
            driver.switch_to.window(whatsapp_handle)
            return True
        else:
            print("❌ WhatsApp tab not found")
            print("Please make sure WhatsApp service is open in Ferdium")
            return False
            
    except Exception as e:
        print(f"❌ Error finding WhatsApp tab: {e}")
        return False

def click_groups_filter(driver):
    """Click on the Groups filter to show only group chats"""
    try:
        print("🔍 Looking for Groups filter button...")
        
        # Wait a bit for the interface to fully load
        time.sleep(3)
        
        # Try different selectors for the groups filter
        group_filter_selectors = [
            "button[title*='Groups']",
            "button[aria-label*='Groups']",
            "div[title*='Groups']",
            "div[aria-label*='Groups']",
            "[data-testid*='filter-group']"
        ]
        
        groups_button = None
        for selector in group_filter_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    groups_button = elements[0]
                    break
            except:
                continue
        
        # Also try XPath for text matching
        if not groups_button:
            try:
                xpath_selector = "//*[contains(text(), 'Groups')]"
                elements = driver.find_elements(By.XPATH, xpath_selector)
                if elements:
                    groups_button = elements[0]
            except:
                pass
        
        if groups_button:
            driver.execute_script("arguments[0].scrollIntoView();", groups_button)
            time.sleep(1)
            groups_button.click()
            print("✅ Groups filter clicked successfully!")
            time.sleep(2)  # Wait for filter to apply
            return True
        else:
            print("⚠️ Groups filter button not found, continuing with all chats...")
            return False
            
    except Exception as e:
        print(f"❌ Error clicking groups filter: {e}")
        print("⚠️ Continuing without groups filter...")
        return False

def get_all_group_names(driver):
    """Extract all group names from the chat list"""
    group_names = []
    processed_names = set()
    scroll_attempts = 0
    max_scroll_attempts = 50
    
    print("📝 Extracting group names...")
    
    try:
        # Find the chat list container
        chat_list_selectors = [
            "div[data-testid='chat-list']",
            "#pane-side",
            "div[role='grid']",
            "div._ak72"
        ]
        
        chat_container = None
        for selector in chat_list_selectors:
            try:
                container = driver.find_element(By.CSS_SELECTOR, selector)
                if container:
                    chat_container = container
                    print(f"✅ Found chat container with selector: {selector}")
                    break
            except:
                continue
        
        if not chat_container:
            print("❌ Could not find chat list container")
            return []
        
        while scroll_attempts < max_scroll_attempts:
            # Get all chat elements
            chat_selectors = [
                "div._ak72",
                "div[role='listitem']",
                "div[data-testid*='chat']",
                "div[tabindex='0'] div._ak72"
            ]
            
            chat_elements = []
            for selector in chat_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        chat_elements = elements
                        break
                except:
                    continue
            
            if not chat_elements:
                print("❌ No chat elements found")
                break
            
            new_names_found = 0
            
            for chat_element in chat_elements:
                try:
                    # Extract chat name
                    name = extract_chat_name(chat_element)
                    
                    if name and name not in processed_names:
                        # Filter for group names (groups usually have multiple participants)
                        if is_likely_group(driver, chat_element, name):
                            group_names.append(name)
                            processed_names.add(name)
                            new_names_found += 1
                            print(f"  📋 {len(group_names):3d}. {name}")
                        else:
                            processed_names.add(name)  # Add to processed to avoid re-checking
                            
                except Exception as e:
                    continue
            
            if new_names_found == 0:
                # No new names found, try scrolling
                try:
                    # Scroll down in the chat list
                    driver.execute_script("arguments[0].scrollTop += 500", chat_container)
                    time.sleep(1)
                    scroll_attempts += 1
                    
                    # Check if we've reached the bottom
                    current_scroll = driver.execute_script("return arguments[0].scrollTop", chat_container)
                    max_scroll = driver.execute_script("return arguments[0].scrollHeight - arguments[0].clientHeight", chat_container)
                    
                    if current_scroll >= max_scroll - 10:  # Near bottom
                        print("📄 Reached end of chat list")
                        break
                        
                except Exception as e:
                    print(f"⚠️ Error scrolling: {e}")
                    break
            else:
                scroll_attempts = 0  # Reset counter when finding new names
        
        print(f"\n✅ Extraction complete! Found {len(group_names)} group chats")
        return group_names
        
    except Exception as e:
        print(f"❌ Error extracting group names: {e}")
        return group_names

def extract_chat_name(chat_element):
    """Extract name from a single chat element"""
    try:
        # Common selectors for chat names
        name_selectors = [
            "span[title]",
            "span._ak8o",
            "span[dir='auto']",
            "div[title]",
            ".copyable-text span",
            "[data-testid*='name']"
        ]
        
        for selector in name_selectors:
            try:
                name_element = chat_element.find_element(By.CSS_SELECTOR, selector)
                name = name_element.get_attribute('title') or name_element.text.strip()
                
                if name and len(name.strip()) > 0 and len(name) < 200:
                    return name.strip()
            except:
                continue
        
        return None
        
    except Exception as e:
        return None

def is_likely_group(driver, chat_element, chat_name):
    """Determine if a chat is likely a group based on various indicators"""
    try:
        # Check for group indicators
        group_indicators = [
            # Group icon indicators
            "svg[data-testid*='group']",
            "span[data-testid*='group']",
            # Multiple participant indicators
            "span:contains('~')",
            # Group admin indicators
            "[title*='admin']",
            "[title*='participant']"
        ]
        
        # Check for visual group indicators
        for indicator in group_indicators:
            try:
                if ":contains" in indicator:
                    # Use XPath for text matching
                    xpath = f".//*[contains(text(), '~')]"
                    if chat_element.find_elements(By.XPATH, xpath):
                        return True
                else:
                    if chat_element.find_elements(By.CSS_SELECTOR, indicator):
                        return True
            except:
                continue
        
        # Check chat name patterns that suggest groups
        group_patterns = [
            # Common group name patterns
            r'.*group.*',
            r'.*team.*',
            r'.*family.*',
            r'.*friends.*',
            r'.*office.*',
            r'.*work.*',
            r'.*project.*',
            r'.*community.*',
            r'.*club.*',
            # Names with multiple words (often groups)
            r'.+ .+ .+',  # 3+ words
            # Names with special characters often used in groups
            r'.*[📱💼🏠🎮🎯⚽].*',
        ]
        
        for pattern in group_patterns:
            if re.match(pattern, chat_name.lower()):
                return True
        
        # If no clear indicators, assume it might be a group if name is longer than typical contact names
        if len(chat_name) > 15:
            return True
            
        return False
        
    except Exception as e:
        # When in doubt, include it
        return True

def save_group_names(group_names, filename="group_names_ferdium.txt"):
    """Save extracted group names to a file"""
    try:
        # Create TXT File directory if it doesn't exist
        os.makedirs("TXT File", exist_ok=True)
        filepath = f"TXT File/{filename}"
        
        # Create backup if file exists
        if os.path.exists(filepath):
            backup_name = f"Backup/{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs("Backup", exist_ok=True)
            import shutil
            shutil.copy2(filepath, backup_name)
            print(f"💾 Backup created: {backup_name}")
        
        # Save group names
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# WhatsApp Group Names Extracted from Ferdium on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total Groups Found: {len(group_names)}\n\n")
            
            for name in group_names:
                f.write(f"{name}\n")
        
        print(f"\n💾 Group names saved to: {filepath}")
        print(f"📊 Total groups saved: {len(group_names)}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving group names: {e}")
        return False

def main():
    """Main function to extract WhatsApp group names from Ferdium"""
    print("📱 WhatsApp Group Name Extractor for Ferdium")
    print("=" * 50)
    
    # Check if Ferdium is running
    if not find_ferdium_debug_port():
        print("\n❌ Ferdium is not running or not accessible")
        print("\n💡 To use this script:")
        print("1. Close Ferdium completely")
        print("2. Start Ferdium with remote debugging:")
        print("   /Applications/Ferdium.app/Contents/MacOS/Ferdium --remote-debugging-port=9222")
        print("3. Open WhatsApp service in Ferdium")
        print("4. Run this script again")
        return
    
    # Setup WebDriver connection to Ferdium
    driver = setup_ferdium_driver()
    if not driver:
        return
    
    try:
        # Find WhatsApp tab
        if not find_whatsapp_tab(driver):
            return
        
        # Wait for WhatsApp to be ready
        print("⏳ Waiting for WhatsApp to load...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='chat-list'], #pane-side"))
        )
        print("✅ WhatsApp loaded successfully!")
        
        # Click groups filter (optional)
        print("\n🔍 Applying Groups filter...")
        groups_filtered = click_groups_filter(driver)
        
        if not groups_filtered:
            print("⚠️ Groups filter not found, extracting from all chats...")
        
        # Extract group names
        print(f"\n📝 Starting group name extraction...")
        print("⏳ This may take a while for large chat lists...")
        
        group_names = get_all_group_names(driver)
        
        if not group_names:
            print("❌ No group names found")
            return
        
        # Save to file
        save_group_names(group_names)
        
        print(f"\n✅ Extraction completed successfully!")
        print(f"📋 Found {len(group_names)} group chats")
        print(f"💾 Saved to: TXT File/group_names_ferdium.txt")
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        
    finally:
        # Don't close the driver since it's connected to Ferdium
        print("\n✅ Extraction complete - Ferdium connection closed")

if __name__ == "__main__":
    # Change to parent directory to access TXT File folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    os.chdir(parent_dir)
    
    main()