#!/usr/bin/env python3
"""
WhatsApp Group Name Extractor
Extracts all group chat names from WhatsApp Web and saves them to a file
Can be used standalone or imported as a function
"""

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import os
import re
from datetime import datetime

def extract_all_group_names(driver, save_to_file=True):
    """
    Main function to extract all WhatsApp group names using existing WebDriver session
    
    Args:
        driver: Existing Selenium WebDriver instance (already logged into WhatsApp Web)
        save_to_file: Whether to save results to file (default: True)
    
    Returns:
        List of group names
    """
    print("📱 WhatsApp Group Name Extractor")
    print("=" * 50)
    
    try:
        # Verify we're on WhatsApp Web and logged in
        if "web.whatsapp.com" not in driver.current_url:
            print("❌ Not on WhatsApp Web. Please navigate to web.whatsapp.com first")
            return []
        
        # Wait for chat list to be loaded
        print("⏳ Waiting for WhatsApp chat list to load...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='chat-list'], #pane-side"))
        )
        
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
            return []
        
        # Save to file if requested
        if save_to_file:
            save_group_names(group_names)
        
        print(f"\n✅ Extraction completed successfully!")
        print(f"📋 Found {len(group_names)} group chats")
        
        return group_names
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        return []

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
            "span:contains('Groups')",
            "[data-testid*='filter-group']",
            "button:contains('Groups')"
        ]
        
        groups_button = None
        for selector in group_filter_selectors:
            try:
                if ":contains" in selector:
                    # Use XPath for text content matching
                    xpath_selector = f"//*[contains(text(), 'Groups')]"
                    elements = driver.find_elements(By.XPATH, xpath_selector)
                    if elements:
                        groups_button = elements[0]
                        break
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        groups_button = elements[0]
                        break
            except:
                continue
        
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

def save_group_names(group_names, filename="group_names.txt"):
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
            f.write(f"# WhatsApp Group Names Extracted on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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
    """Main function when running as standalone script (creates new WebDriver)"""
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.service import Service
        from selenium.webdriver.firefox.options import Options
        from webdriver_manager.firefox import GeckoDriverManager
        
        print("📱 WhatsApp Group Name Extractor (Standalone Mode)")
        print("=" * 50)
        
        # Setup WebDriver
        print("🔧 Setting up Firefox WebDriver...")
        
        firefox_options = Options()
        firefox_options.add_argument("--disable-blink-features=AutomationControlled")
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference('useAutomationExtension', False)
        firefox_options.add_argument("--disable-extensions")
        
        # Use the same profile as main script
        profile_path = "/Users/admin/Library/Application Support/Firefox/Profiles/focg601r.NepalWin"
        try:
            if os.path.exists(profile_path):
                firefox_options.profile = webdriver.FirefoxProfile(profile_path)
                print(f"✅ Using Firefox profile: {profile_path}")
            else:
                print(f"⚠️ Profile not found: {profile_path}")
                print("Using default Firefox profile...")
        except Exception as e:
            print(f"⚠️ Error loading profile: {e}")
            print("Using default Firefox profile...")
        
        # Create service
        service = Service(GeckoDriverManager().install())
        
        # Create driver
        driver = webdriver.Firefox(service=service, options=firefox_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("✅ Firefox WebDriver setup complete")
        
        try:
            # Navigate to WhatsApp Web
            print("🌐 Opening WhatsApp Web...")
            driver.get("https://web.whatsapp.com")
            
            # Check if already logged in or need to scan QR
            print("⏳ Checking login status...")
            try:
                # Try to find chat list directly (already logged in)
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='chat-list'], #pane-side"))
                )
                print("✅ Already logged in to WhatsApp Web!")
            except:
                # Need to scan QR code
                print("📱 Please scan the QR code with your phone to login to WhatsApp Web")
                print("⏳ Waiting for WhatsApp to load...")
                
                WebDriverWait(driver, 120).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='chat-list'], #pane-side"))
                )
                print("✅ WhatsApp Web loaded successfully!")
            
            # Extract group names using existing function
            group_names = extract_all_group_names(driver, save_to_file=True)
            
            if group_names:
                print(f"💾 Saved to: TXT File/group_names.txt")
            
        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            
        finally:
            # Clean up
            try:
                driver.quit()
                print("\n🔧 Browser closed")
            except:
                pass
                
    except ImportError as e:
        print(f"❌ Missing required packages: {e}")
        print("Please install selenium and webdriver-manager:")
        print("pip install selenium webdriver-manager")
    except Exception as e:
        print(f"❌ Error setting up WebDriver: {e}")

if __name__ == "__main__":
    # Change to parent directory to access TXT File folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    os.chdir(parent_dir)
    
    main()