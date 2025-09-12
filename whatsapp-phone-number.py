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
from datetime import datetime, timedelta
from collections import defaultdict
from tqdm import tqdm
import pyperclip
import re
import signal
import sys
import threading

# Import group name extractor
try:
    from tools.extract_group_names import extract_all_group_names
    GROUP_EXTRACTOR_AVAILABLE = True
except ImportError:
    GROUP_EXTRACTOR_AVAILABLE = False
    print("⚠️  Warning: Group name extractor not available")

# Try to import keyboard, make it optional
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("⚠️  Warning: 'keyboard' library not installed. Ctrl+P pause functionality will not work.")
    print("   Install with: pip install keyboard")

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
    os._exit(0)  # Force immediate exit

def toggle_pause():
    """Toggle pause state when Ctrl+P is pressed"""
    global script_paused
    with pause_lock:
        script_paused = not script_paused
        if script_paused:
            print("\n⏸️  Script PAUSED - Press Ctrl+P again to continue...")
        else:
            print("\n▶️  Script RESUMED - Continuing execution...")

def setup_keyboard_listener():
    """Setup keyboard listener for pause/continue functionality"""
    if not KEYBOARD_AVAILABLE:
        print("🎮 Keyboard listener not available - install 'keyboard' library for Ctrl+P functionality")
        return
        
    try:
        keyboard.add_hotkey('ctrl+p', toggle_pause)
        print("🎮 Keyboard listener setup complete")
    except Exception as e:
        print(f"⚠️ Warning: Could not setup keyboard listener: {e}")
        print("🎮 Pause functionality may not work properly")



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
    
    # Handle pause state
    while script_paused:
        time.sleep(0.1)  # Small delay to prevent CPU spinning
        if script_stopped:  # Check if stop was requested during pause
            print("Script stopped by user")
            try:
                driver.quit()
            except:
                pass
            sys.exit(0)

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, signal_handler)
    setup_keyboard_listener()
    
    if KEYBOARD_AVAILABLE:
        print("🎮 Controls: Ctrl+C = Stop | Ctrl+P = Pause/Continue")
    else:
        print("🎮 Controls: Ctrl+C = Stop")

def wait_for_user_input(message="Press ENTER to continue..."):
    """Pause execution until user presses ENTER in terminal"""
    try:
        input(message)
        print("Continuing...")
    except KeyboardInterrupt:
        print("\n🛑 Script interrupted by user - Exiting completely...")
        try:
            driver.quit()
        except:
            pass
        sys.exit(0)
    return True

def get_action_selection():
    """Get user input for what action to perform"""
    print("\n" + "="*60)
    print("🎯 WHATSAPP AUTOMATION - SELECT ACTION")
    print("="*60)
    print("1. 📱 Send messages to phone numbers")
    print("2. 📋 Extract all group chat names") 
    print("3. ❌ Exit")
    print("="*60)
    
    while True:
        try:
            choice = input("Enter your choice (1-3): ").strip()
            if choice == "1":
                return "send_messages"
            elif choice == "2":
                return "extract_groups"
            elif choice == "3":
                return "exit"
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
        except KeyboardInterrupt:
            print("\n🛑 Script interrupted by user - Exiting completely...")
            try:
                driver.quit()
            except:
                pass
            sys.exit(0)
        except Exception as e:
            print(f"❌ Error getting input: {e}")
            return "exit"

def get_row_selection():
    """Get user input for row selection from phone_number.txt (supports phone numbers and group names)"""
    try:
        # First, show how many entries are available (phones + groups)
        try:
            with open("TXT File/phone_number.txt", "r", encoding="utf-8") as f:
                phone_count = 0
                group_count = 0
                for line in f:
                    entry = line.strip()
                    if entry:
                        # Check if it's a phone number
                        cleaned_entry = entry.replace(" ", "").replace("-", "").replace("+", "")
                        if re.match(r'^\d{10,15}$', cleaned_entry):
                            phone_count += 1
                        else:
                            group_count += 1
                            
                total_numbers = phone_count + group_count
        except FileNotFoundError:
            print("❌ phone_number.txt not found")
            return None, None, 0
        
        print(f"\n📊 Total entries in file: {total_numbers} ({phone_count} phones + {group_count} groups)")
        print("\n🎯 Row Selection Options:")
        print("1. Process all entries (default)")
        print("2. Start from specific row")
        print("3. Process specific range")
        
        try:
            choice = input("\nEnter your choice (1-3) or press ENTER for default: ").strip()
            
            if not choice or choice == "1":
                return None, None, total_numbers
            
            elif choice == "2":
                start_row = input(f"Enter starting row (1-{total_numbers}): ").strip()
                if not start_row.isdigit():
                    print("Invalid input, using default (all numbers)")
                    return None, None, total_numbers
                start_row = int(start_row)
                if start_row < 1 or start_row > total_numbers:
                    print(f"Row must be between 1 and {total_numbers}, using default")
                    return None, None, total_numbers
                return start_row, None, total_numbers
            
            elif choice == "3":
                start_row = input(f"Enter starting row (1-{total_numbers}): ").strip()
                max_rows = input("Enter number of rows to process: ").strip()
                
                if not start_row.isdigit() or not max_rows.isdigit():
                    print("Invalid input, using default (all numbers)")
                    return None, None, total_numbers
                    
                start_row = int(start_row)
                max_rows = int(max_rows)
                
                if start_row < 1 or start_row > total_numbers:
                    print(f"Starting row must be between 1 and {total_numbers}, using default")
                    return None, None, total_numbers
                    
                if max_rows < 1:
                    print("Number of rows must be positive, using default")
                    return None, None, total_numbers
                    
                return start_row, max_rows, total_numbers
            
            else:
                print("Invalid choice, using default (all numbers)")
                return None, None, total_numbers
                
        except KeyboardInterrupt:
            print("\n🛑 Script interrupted by user - Exiting completely...")
            try:
                driver.quit()
            except:
                pass
            sys.exit(0)
            
    except Exception as e:
        print(f"Error in row selection: {e}")
        return None, None, 0

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

def load_exclude_words():
    """Load exclude words from exclude_words.txt file"""
    try:
        with open('TXT File/exclude_words.txt', 'r', encoding='utf-8') as f:
            words = [line.strip() for line in f.readlines() if line.strip()]
            return words if words else ["NepalWin", "NPW", "Blocked"]
    except FileNotFoundError:
        print("⚠️ exclude_words.txt not found, using default exclude words")
        return ["NepalWin", "NPW", "Blocked"]

def click_non_excluded_names(driver, exclude_words=None):
    if exclude_words is None:
        exclude_words = load_exclude_words()
    
    try:
        # Wait for the tag suggestion container
        container = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.xc9l9hb.x10l6tqk.x1lliihq"))
        )

        # Now only look for names inside this container
        name_elements = container.find_elements(By.CSS_SELECTOR, "span._ao3e")

        for elem in name_elements:
            # Check for pause/stop before processing each name
            check_script_control()
            
            name_text = elem.text.strip()
            print(f"\033[94m[DEBUG]\033[0m Found name element text: '{name_text}'")
            
            # Check if any exclude word is in the name (case insensitive)
            should_exclude = any(exclude_word.lower() in name_text.lower() for exclude_word in exclude_words)
            
            if name_text and not should_exclude:
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                    elem.click()
                    print(f"\033[92m[APPROVED]\033[0m Clicked on: \033[92m{name_text}\033[0m")
                    return True
                except Exception as e:
                    print(f"\033[91m[WARN]\033[0m Could not click {name_text}: {repr(e)}")
                    continue

        print(f"\033[93m[INFO]\033[0m No names found without {exclude_words} inside container")
        return False

    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Could not retrieve names: {repr(e)}")
        return False



def loop_through_numbers(start_row=None, max_rows=None, total_numbers=None):
    """Loop through phone numbers AND group chat names from phone_number.txt and search for them
    
    Args:
        start_row (int): Starting row number (1-based index, None = start from beginning)
        max_rows (int): Maximum number of rows to process (None = process all)
    """
    # Initialize statistics
    successful_numbers = 0
    failed_numbers = 0
    
    # Add timestamp to not_in_group.txt at start of processing
    try:
        with open("TXT File/not_in_group.txt", "a", encoding="utf-8") as f:
            # GMT+7 timezone (7 hours ahead of UTC)
            gmt_plus_7 = datetime.utcnow() + timedelta(hours=7)
            timestamp = gmt_plus_7.strftime("%Y-%m-%d %H:%M:%S GMT+7")
            f.write(f"\n=== Processing started: {timestamp} ===\n")
        print(f"📅 GMT+7 Timestamp recorded in not_in_group.txt")
    except Exception as e:
        print(f"⚠️ Could not write timestamp: {e}")
    
    try:
        # Load phone numbers AND group chat names from file
        all_entries = []
        phone_count = 0
        group_count = 0
        
        with open("TXT File/phone_number.txt", "r", encoding="utf-8") as f:
            for line in f:
                entry = line.strip()
                if entry:
                    # Check if it's a phone number (digits only, with optional + and spaces/dashes)
                    cleaned_entry = entry.replace(" ", "").replace("-", "").replace("+", "")
                    if re.match(r'^\d{10,15}$', cleaned_entry):
                        # It's a phone number
                        all_entries.append({
                            'type': 'phone',
                            'value': cleaned_entry,
                            'original': entry
                        })
                        phone_count += 1
                    else:
                        # It's likely a group chat name
                        all_entries.append({
                            'type': 'group',
                            'value': entry,
                            'original': entry
                        })
                        group_count += 1
        
        if not all_entries:
            print("❌ No valid entries found in phone_number.txt")
            return False
        
        print(f"📊 Loaded {phone_count} phone numbers and {group_count} group chat names")
        
        # Apply row filtering
        if start_row is not None:
            start_index = max(0, start_row - 1)  # Convert to 0-based index
            all_entries = all_entries[start_index:]
            
        if max_rows is not None:
            all_entries = all_entries[:max_rows]
            
        entries_to_process = all_entries
        
        if not entries_to_process:
            print("❌ No entries found in specified range")
            return False
        
        range_info = ""
        if start_row or max_rows:
            start_display = start_row if start_row else 1
            end_display = (start_display + len(entries_to_process) - 1) if entries_to_process else start_display
            range_info = f" (rows {start_display}-{end_display})"
            
        print(f"📞 Processing {len(entries_to_process)} entries (phones + groups) from file{range_info}")
        
        for row_index, entry in enumerate(entries_to_process, start=1):
            # Check for pause/stop before processing each number
            check_script_control()
            
            # Calculate actual row number considering start_row offset
            actual_row = (start_row if start_row else 1) + row_index - 1
            
            # Extract the search value and type
            search_value = entry['value']
            entry_type = entry['type']
            original_entry = entry['original']
            
            if entry_type == 'phone':
                print(f"🔍 Processing phone number: {search_value}")
            else:
                print(f"🔍 Processing group chat: {search_value}")
            
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
                    print(f"❌ Could not find search box for entry {search_value}")
                    continue

                # Scroll into view and click
                driver.execute_script("arguments[0].scrollIntoView(true);", search_box)
                time.sleep(0.5)
                
                # Click using ActionChains for better reliability
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(driver).move_to_element(search_box).click().perform()
                time.sleep(0.5)
                
                # Copy to clipboard first
                pyperclip.copy(search_value)
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
                time.sleep(.5)
                
                print(f"\033[92m[APPROVED]\033[0m Pasted entry into search: {search_value}")


                # --- Check for "No chats, contacts or messages found" ---
                try:
                    no_result = WebDriverWait(driver, 2, poll_frequency=0.2).until(
                        EC.presence_of_element_located((
                            By.XPATH,
                            "//span[contains(text(), 'No chats, contacts or messages found')]"
                        ))
                    )
                    if no_result.is_displayed():
                        print(f"\033[91m[WARN]\033[0m No chat found for {search_value}")
                        with open("TXT File/not_in_group.txt", "a", encoding="utf-8") as f:
                            f.write(f"{original_entry}\n")
                        print(f"\033[93m[RECORDED]\033[0m Entry \033[93m{search_value}\033[0m saved to not_in_group.txt")
                        failed_numbers += 1
                        continue  # jump to next number in your loop

                except TimeoutException:
                    # No such span -> safe to continue normal flow
                    pass
                
                # Verify the content was pasted
                # time.sleep(0.5)
                current_value = search_box.get_attribute('value') or driver.execute_script("return arguments[0].innerText;", search_box)
                if search_value not in str(current_value):
                    print(f"⚠️ Paste may have failed, trying direct input...")
                    # Fallback: direct character input
                    search_box.clear()
                    for char in search_value:
                        search_box.send_keys(char)
                        time.sleep(0.05)
                
                # Different handling based on entry type
                if entry_type == 'group':
                    # For group chats (alphabetic entries): Priority order - Groups in common > Chats > Contact
                    groups_common_success = False
                    time.sleep(.5)
                    
                    # Check what sections are available
                    groups_in_common_found = False
                    chats_found = False
                    contact_found = False
                    
                    try:
                        # Check for "Groups in common" section
                        driver.find_element(By.XPATH, "//div[@role='listitem' and contains(., 'Groups in common')]")
                        groups_in_common_found = True
                        print("[INFO] Found 'Groups in common' section")
                    except:
                        pass
                    
                    try:
                        # Check for "Chats" section
                        driver.find_element(By.XPATH, "//div[@role='listitem' and contains(., 'Chats')]")
                        chats_found = True
                        print("[INFO] Found 'Chats' section")
                    except:
                        pass
                    
                    try:
                        # Check for "Contact" section
                        driver.find_element(By.XPATH, "//div[@role='listitem' and contains(., 'Contact')]")
                        contact_found = True
                        print("[INFO] Found 'Contact' section")
                    except:
                        pass
                    
                    # If ONLY 'Contact' section found, skip immediately
                    if contact_found and not groups_in_common_found and not chats_found:
                        print(f"[WARN] Only 'Contact' section found for: {search_value} - skipping (individual contact only)")
                        # Record the entry in not_in_group.txt
                        with open("TXT File/not_in_group.txt", "a", encoding="utf-8") as f:
                            f.write(f"{original_entry}\n")
                        print(f"\033[93m[RECORDED]\033[0m Contact-only entry {search_value} saved to not_in_group.txt")
                        failed_numbers += 1
                        continue
                    
                    # Priority 1: Try "Groups in common" first
                    if groups_in_common_found and not groups_common_success:
                        try:
                            print("[INFO] Trying 'Groups in common' (Priority 1)")
                            # Wait for the next sibling div (the chat after 'Groups in common')
                            next_chat = WebDriverWait(driver, 2, poll_frequency=0.2).until(
                                EC.element_to_be_clickable((
                                    By.XPATH,
                                    "//div[@role='listitem' and contains(., 'Groups in common')]/following-sibling::div[1]"
                                ))
                            )
                            
                            # Scroll into view and click
                            driver.execute_script("arguments[0].scrollIntoView();", next_chat)
                            next_chat.click()
                            print("[SUCCESS] Clicked chat after 'Groups in common'")
                            groups_common_success = True
                            
                        except Exception as e:
                            print(f"[INFO] 'Groups in common' click failed: {e}")
                    
                    # Priority 2: Try "Chats" if Groups in common failed
                    if chats_found and not groups_common_success:
                        try:
                            print("[INFO] Trying 'Chats' section (Priority 2)")
                            # Try to find chat under "Chats" section
                            chat_found = WebDriverWait(driver, 2, poll_frequency=0.1).until(
                                EC.element_to_be_clickable((
                                    By.XPATH,
                                    "//div[@role='listitem' and contains(., 'Chats')]/following-sibling::div[1]"
                                ))
                            )
                            
                            # Click on the found chat
                            driver.execute_script("arguments[0].scrollIntoView();", chat_found)
                            time.sleep(0.5)
                            chat_found.click()
                            print(f"[INFO] Clicked on chat under 'Chats': {search_value}")
                            
                            # Wait for chat to load and verify it's a group chat
                            time.sleep(1)
                            is_group_chat = False
                            
                            try:
                                # Method 1: Check for group info icon (more reliable)
                                group_info_selectors = [
                                    "div[data-testid='conversation-info-header-group']",
                                    "span[data-icon='group']",
                                    "div[data-testid='group-info']",
                                    "span[title*='participant']",
                                    "span[title*='member']"
                                ]
                                
                                for selector in group_info_selectors:
                                    if driver.find_elements(By.CSS_SELECTOR, selector):
                                        is_group_chat = True
                                        print("[INFO] Confirmed: This is a group chat (found group indicator)")
                                        break
                                
                                # Method 2: Check chat header text for group indicators
                                if not is_group_chat:
                                    try:
                                        header_elements = driver.find_elements(By.CSS_SELECTOR, "header span, header div")
                                        for element in header_elements:
                                            header_text = element.text.lower()
                                            if any(indicator in header_text for indicator in ['participant', 'member', 'you, ', ', you']):
                                                is_group_chat = True
                                                print("[INFO] Confirmed: This is a group chat (found participant info)")
                                                break
                                    except:
                                        pass
                                
                                # Method 3: Check for group-specific elements
                                if not is_group_chat:
                                    try:
                                        group_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Group') or contains(text(), 'Admin') or contains(@aria-label, 'Group')]")
                                        if group_elements:
                                            is_group_chat = True
                                            print("[INFO] Confirmed: This is a group chat (found group elements)")
                                    except:
                                        pass
                                        
                            except Exception as e:
                                print(f"[WARN] Could not verify if chat is a group: {e}")
                            
                            if is_group_chat:
                                print(f"[SUCCESS] Verified group chat under 'Chats' for: {search_value}")
                                groups_common_success = True
                            else:
                                print(f"[WARN] Chat under 'Chats' appears to be individual, not group for: {search_value}")
                                # Go back to search to avoid sending to wrong chat
                                search_box = driver.find_element(By.XPATH, "//div[@contenteditable='true'][@data-tab='3']")
                                search_box.click()
                                time.sleep(0.5)
                                
                        except Exception as e:
                            print(f"[INFO] 'Chats' section failed: {e}")
                    
                    # Final check - if nothing worked, record as failed
                    if not groups_common_success:
                        print(f"\033[91m[WARN]\033[0m All sections failed for group: {search_value}")
                        # Record the entry in not_in_group.txt
                        with open("TXT File/not_in_group.txt", "a", encoding="utf-8") as f:
                            f.write(f"{original_entry}\n")
                        print(f"\033[93m[RECORDED]\033[0m Group {search_value} saved to not_in_group.txt")
                        failed_numbers += 1
                        continue
                    
                    # Send message if any method succeeded
                    if groups_common_success:
                        print(f"\033[1;32m[{actual_row}/{total_numbers}]\033[0m [INFO] Sending message to group: {search_value}")
                        send_message_from_file()
                        successful_numbers += 1
                        time.sleep(.5)
                        
                else:
                    # For phone numbers: use the original "Groups in common" logic
                    try:
                        # Wait for the "Groups in common" div to appear
                        groups_in_common = WebDriverWait(driver, 20, poll_frequency=0.2).until(
                            EC.presence_of_element_located((
                                By.XPATH,
                                "//div[@role='listitem' and contains(., 'Groups in common')]"
                            ))
                        )

                        # Wait for the next sibling div (the chat after 'Groups in common')
                        next_chat = WebDriverWait(driver, 20, poll_frequency=0.2).until(
                            EC.element_to_be_clickable((
                                By.XPATH,
                                "//div[@role='listitem' and contains(., 'Groups in common')]/following-sibling::div[1]"
                            ))
                        )

                        # Scroll into view and click
                        driver.execute_script("arguments[0].scrollIntoView();", next_chat)
                        next_chat.click()
                        print("[INFO] Clicked chat after 'Groups in common'")
                        
                        # Send message from file
                        print(f"\033[1;32m[{actual_row}/{total_numbers}]\033[0m [INFO] Sending message to chat for phone: {search_value}")
                        send_message_from_file()
                        successful_numbers += 1
                        time.sleep(.5)

                    except Exception:
                        print(f"\033[91m[WARN]\033[0m 'Groups in common' not found for phone: {search_value}")
                        # Record the entry in not_in_group.txt
                        with open("TXT File/not_in_group.txt", "a", encoding="utf-8") as f:
                            f.write(f"{original_entry}\n")
                        print(f"\033[93m[RECORDED]\033[0m Phone {search_value} saved to not_in_group.txt")
                        failed_numbers += 1
                        continue

                

                # Wait a bit before next number
                time.sleep(.7)

            except Exception as e:
                print(f"⚠️ Could not process entry {search_value}: {repr(e)}")
                failed_numbers += 1
                continue

        # Print completion statistics
        print("\n" + "="*60)
        print("📊 PROCESSING COMPLETED!")
        print("="*60)
        print(f"✅ Successful messages sent: {successful_numbers}")
        print(f"❌ Entries not found/failed: {failed_numbers}")
        print(f"📞 Total entries processed: {successful_numbers + failed_numbers}")
        
        # Count entries in not_in_group.txt file
        try:
            with open("TXT File/not_in_group.txt", "r", encoding="utf-8") as f:
                not_found_count = len([line for line in f if line.strip()])
            print(f"📝 Entries recorded in not_in_group.txt: {not_found_count}")
        except FileNotFoundError:
            print(f"📝 Entries recorded in not_in_group.txt: 0")
        
        print("="*60)
        print("🎉 All entries processed successfully!")
        
        # Add completion timestamp to not_in_group.txt
        try:
            with open("TXT File/not_in_group.txt", "a", encoding="utf-8") as f:
                # GMT+7 timezone (7 hours ahead of UTC)
                gmt_plus_7 = datetime.utcnow() + timedelta(hours=7)
                timestamp = gmt_plus_7.strftime("%Y-%m-%d %H:%M:%S GMT+7")
                f.write(f"=== Processing completed: {timestamp} ===\n\n")
            print(f"📅 GMT+7 Completion timestamp recorded in not_in_group.txt")
        except Exception as e:
            print(f"⚠️ Could not write completion timestamp: {e}")
        
        print("Closing browser in 5 seconds...")
        time.sleep(5)
        
        return True

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

    time.sleep(.5)
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
        time.sleep(.5)

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
                time.sleep(1)
                
                print(f"[INFO] Image pasted from clipboard: {os.path.basename(image_path)}")
                time.sleep(1)
                # Send the message using Enter key
                # wait for the button to be clickable
                send_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[@role="button" and @aria-label="Send"]'))
                )

                send_button.click()
                print("[INFO] Message + image sent successfully!")
                time.sleep(1.5)
                
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
        filename = "TXT File/description.txt"
        
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


profile_path = "/Users/admin/Library/Application Support/Firefox/Profiles/focg601r.NepalWin"

options = Options()
try:
    if os.path.exists(profile_path):
        options.profile = webdriver.FirefoxProfile(profile_path)
        print(f"✅ Using Firefox profile: {profile_path}")
    else:
        print(f"⚠️ Profile not found: {profile_path}")
        print("Using default Firefox profile...")
except Exception as e:
    print(f"⚠️ Error loading profile: {e}")
    print("Using default Firefox profile...")

# Anti-detection measures
options.set_preference("dom.webdriver.enabled", False)
options.set_preference("useAutomationExtension", False)
options.set_preference("general.useragent.override", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0")

# Headless mode if needed
# options.add_argument('--headless')

# Setup the driver
try:
    service = Service(GeckoDriverManager().install())
    print("✅ GeckoDriver service created")
    
    print("🔄 Starting Firefox browser...")
    driver = webdriver.Firefox(service=service, options=options)
    print("✅ Firefox started successfully!")
    
    driver.maximize_window()
    print("✅ Browser window maximized")
    
except Exception as e:
    print(f"❌ Failed to start Firefox: {e}")
    print("This might be due to:")
    print("1. Firefox not installed")
    print("2. Profile issues")
    print("3. GeckoDriver compatibility")
    print("Please install Firefox or check your profile settings.")
    sys.exit(1)

# Setup signal handlers for pause/stop controls
setup_signal_handlers()

driver.get("https://web.whatsapp.com/")

# Wait and check if login is required
try:
    # Check if WhatsApp Web header is present (means not logged in)
    login_header = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'x3nfvp2')]//h1[text()='WhatsApp Web']"))
    )

    # Get user action selection
    action = get_action_selection()
    
    if action == "exit":
        print("👋 Exiting...")
    elif action == "extract_groups":
        if GROUP_EXTRACTOR_AVAILABLE:
            print("\n🔄 Starting group name extraction...")
            group_names = extract_all_group_names(driver, save_to_file=True)
            if group_names:
                print(f"✅ Successfully extracted {len(group_names)} group names!")
            else:
                print("❌ No group names found or extraction failed")
        else:
            print("❌ Group name extractor is not available")
    elif action == "send_messages":
        # Get user input for row selection
        start_row, max_rows, total_numbers = get_row_selection()
        
        # Pause here to allow user adjust position
        time.sleep(1)
        processing_result = loop_through_numbers(start_row, max_rows, total_numbers)    
        # loop_through_all_chats_with_scroll()

except:
    print("WhatsApp Web header not found - already logged in")
    
    # Get user action selection
    action = get_action_selection()
    
    if action == "exit":
        print("👋 Exiting...")
    elif action == "extract_groups":
        if GROUP_EXTRACTOR_AVAILABLE:
            print("\n🔄 Starting group name extraction...")
            group_names = extract_all_group_names(driver, save_to_file=True)
            if group_names:
                print(f"✅ Successfully extracted {len(group_names)} group names!")
            else:
                print("❌ No group names found or extraction failed")
        else:
            print("❌ Group name extractor is not available")
    elif action == "send_messages":
        # Get user input for row selection
        start_row, max_rows, total_numbers = get_row_selection()
        
        # Click the Groups filter button
        time.sleep(2)
        processing_result = loop_through_numbers(start_row, max_rows, total_numbers)
        # loop_through_all_chats_with_scroll()

# Process complete - close browser
try:
    print("\n🔄 Shutting down browser...")
    driver.quit()
    print("✅ Browser closed successfully!")
except Exception as e:
    print(f"⚠️ Error closing browser: {e}")

sys.exit(0)





