#!/usr/bin/env python3
"""
Phone Number Cleanup Utility
Removes +, spaces, dashes, and other non-digit characters from phone numbers
"""

import re
import os
import shutil
from datetime import datetime

def cleanup_phone_numbers(input_file="TXT File/phone_number.txt", output_file=None):
    """
    Clean phone numbers by removing +, spaces, dashes and other non-digit characters
    
    Args:
        input_file (str): Path to input file containing phone numbers
        output_file (str): Path to output file (if None, overwrites input file)
    """
    if not os.path.exists(input_file):
        print(f"❌ File {input_file} not found!")
        return False
    
    try:
        # Create backup in Backup folder before making changes
        os.makedirs("Backup", exist_ok=True)
        filename_only = os.path.basename(input_file)
        backup_path = f"Backup/{filename_only}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copy2(input_file, backup_path)
            print(f"💾 Backup created: {backup_path}")
        except Exception as e:
            print(f"⚠️ Could not create backup: {e}")
        
        # Read all numbers
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        cleaned_numbers = []
        original_count = 0
        
        for line in lines:
            line = line.strip()
            if line:
                original_count += 1
                # Remove everything except digits
                cleaned_number = re.sub(r'[^\d]', '', line)
                if cleaned_number:  # Only add if there are digits left
                    cleaned_numbers.append(cleaned_number)
        
        # Write cleaned numbers
        output_path = output_file if output_file else input_file
        with open(output_path, 'w', encoding='utf-8') as f:
            for number in cleaned_numbers:
                f.write(f"{number}\n")
        
        print(f"✅ Cleanup completed!")
        print(f"📊 Original numbers: {original_count}")
        print(f"📊 Cleaned numbers: {len(cleaned_numbers)}")
        print(f"📊 Removed: {original_count - len(cleaned_numbers)} invalid entries")
        print(f"💾 Saved to: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False

def preview_cleanup(input_file="TXT File/phone_number.txt", lines_to_show=10):
    """Preview what the cleanup will do without making changes"""
    if not os.path.exists(input_file):
        print(f"❌ File {input_file} not found!")
        return
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:lines_to_show]
        
        print(f"🔍 Preview of cleanup (first {lines_to_show} lines):")
        print("=" * 50)
        
        for i, line in enumerate(lines, 1):
            original = line.strip()
            if original:
                cleaned = re.sub(r'[^\d]', '', original)
                print(f"{i:2d}. '{original}' → '{cleaned}'")
        
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error during preview: {e}")

if __name__ == "__main__":
    # Change to parent directory to access TXT File folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    os.chdir(parent_dir)
    
    print("📞 Phone Number Cleanup Utility")
    print("=" * 40)
    
    # Check if file exists
    if not os.path.exists("TXT File/phone_number.txt"):
        print("❌ phone_number.txt not found in TXT File directory!")
        exit(1)
    
    # Show preview
    preview_cleanup("TXT File/phone_number.txt")
    
    # Ask for confirmation
    response = input("\nProceed with cleanup? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        cleanup_phone_numbers("TXT File/phone_number.txt")
    else:
        print("❌ Cleanup cancelled.")