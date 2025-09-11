#!/usr/bin/env python3
"""
Phone Number Removal Utility
Remove specific numbers from phone_number.txt by providing a list of numbers to remove
"""

import os
import re
from datetime import datetime

def clean_number(number):
    """
    Clean a number by removing +, spaces, dashes and keeping only digits
    
    Examples:
        '+977 982 466 6101' → '9779824666101'
        '+9779824666101' → '9779824666101' 
        '977-982-466-6101' → '9779824666101'
    
    This ensures that numbers with different formatting will still match
    when comparing against the cleaned numbers in phone_number.txt
    """
    return re.sub(r'[^\d]', '', str(number).strip())

def load_phone_numbers(file_path="TXT File/phone_number.txt"):
    """Load all phone numbers from file"""
    if not os.path.exists(file_path):
        print(f"❌ File {file_path} not found!")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            numbers = []
            for line in f:
                line = line.strip()
                if line:
                    cleaned = clean_number(line)
                    if cleaned:
                        numbers.append(cleaned)
            return numbers
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return []

def remove_numbers_from_list(numbers_to_remove, input_file="TXT File/phone_number.txt", output_file=None):
    """
    Remove specified numbers from phone_number.txt
    
    Args:
        numbers_to_remove (list): List of numbers to remove
        input_file (str): Input file path
        output_file (str): Output file path (if None, overwrites input file)
    """
    # Load current numbers
    current_numbers = load_phone_numbers(input_file)
    if not current_numbers:
        return False
    
    # Clean the numbers to remove
    cleaned_remove_list = [clean_number(num) for num in numbers_to_remove if clean_number(num)]
    
    if not cleaned_remove_list:
        print("❌ No valid numbers provided to remove!")
        return False
    
    # Create set for faster lookup
    remove_set = set(cleaned_remove_list)
    
    # Filter out numbers to remove
    original_count = len(current_numbers)
    filtered_numbers = [num for num in current_numbers if num not in remove_set]
    removed_count = original_count - len(filtered_numbers)
    
    # Show what will be removed
    print(f"\n📊 REMOVAL SUMMARY:")
    print(f"Original count: {original_count}")
    print(f"Numbers to remove: {len(cleaned_remove_list)}")
    print(f"Actually found and removed: {removed_count}")
    print(f"Remaining count: {len(filtered_numbers)}")
    
    if removed_count == 0:
        print("⚠️ No numbers were found to remove!")
        return False
    
    # Show which numbers were found for removal
    found_to_remove = [num for num in cleaned_remove_list if num in current_numbers]
    if found_to_remove:
        print(f"\n🗑️ Numbers found and will be removed:")
        for i, num in enumerate(found_to_remove[:10], 1):  # Show first 10
            print(f"  {i:2d}. {num}")
        if len(found_to_remove) > 10:
            print(f"     ... and {len(found_to_remove) - 10} more")
    
    # Show which numbers were NOT found
    not_found = [num for num in cleaned_remove_list if num not in current_numbers]
    if not_found:
        print(f"\n⚠️ Numbers NOT found in file:")
        for i, num in enumerate(not_found[:5], 1):  # Show first 5
            print(f"  {i:2d}. {num}")
        if len(not_found) > 5:
            print(f"     ... and {len(not_found) - 5} more")
    
    # Write filtered numbers
    output_path = output_file if output_file else input_file
    
    # Create backup in Backup folder
    import os
    os.makedirs("Backup", exist_ok=True)
    filename_only = os.path.basename(input_file)
    backup_path = f"Backup/{filename_only}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(input_file, backup_path)
        print(f"\n💾 Backup created: {backup_path}")
    except Exception as e:
        print(f"⚠️ Could not create backup: {e}")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for number in filtered_numbers:
                f.write(f"{number}\n")
        
        print(f"\n✅ Numbers removed successfully!")
        print(f"💾 Updated file: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        return False

def remove_numbers_interactive():
    """Interactive mode to input numbers to remove"""
    print("📞 Phone Number Removal Tool")
    print("=" * 40)
    
    # Check if file exists
    if not os.path.exists("TXT File/phone_number.txt"):
        print("❌ phone_number.txt not found in TXT File directory!")
        return
    
    # Show current count
    current_numbers = load_phone_numbers()
    print(f"📊 Current phone numbers in file: {len(current_numbers)}")
    
    print("\n📝 Enter numbers to remove (one per line):")
    print("   • You can paste a list of numbers")
    print("   • Any format works: +9779824666101, +977 982 466 6101, etc.")
    print("   • Numbers will be automatically cleaned and matched")
    print("   • Press Ctrl+D (Mac/Linux) or Ctrl+Z (Windows) when done")
    print("   • Or type 'DONE' on a new line")
    print("-" * 40)
    
    numbers_to_remove = []
    try:
        while True:
            try:
                line = input().strip()
                if line.upper() == 'DONE':
                    break
                if line:
                    numbers_to_remove.append(line)
            except EOFError:
                break
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return
    
    if not numbers_to_remove:
        print("❌ No numbers provided to remove!")
        return
    
    print(f"\n📝 You provided {len(numbers_to_remove)} numbers to remove")
    
    # Ask for confirmation
    response = input("\nProceed with removal? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        remove_numbers_from_list(numbers_to_remove)
    else:
        print("❌ Removal cancelled.")

def remove_numbers_from_file(remove_file_path):
    """Remove numbers listed in a separate file"""
    if not os.path.exists(remove_file_path):
        print(f"❌ Remove list file {remove_file_path} not found!")
        return False
    
    try:
        with open(remove_file_path, 'r', encoding='utf-8') as f:
            numbers_to_remove = [line.strip() for line in f if line.strip()]
        
        print(f"📄 Loaded {len(numbers_to_remove)} numbers from {remove_file_path}")
        return remove_numbers_from_list(numbers_to_remove)
        
    except Exception as e:
        print(f"❌ Error reading remove list file: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    # Change to parent directory to access TXT File folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    os.chdir(parent_dir)
    
    if len(sys.argv) > 1:
        # File mode: python remove_numbers.py remove_list.txt
        remove_file = sys.argv[1]
        print(f"📄 Reading numbers to remove from: {remove_file}")
        remove_numbers_from_file(remove_file)
    else:
        # Interactive mode
        remove_numbers_interactive()