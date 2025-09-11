import sys
import os
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                             QWidget, QTextEdit, QPushButton, QLabel, QFileDialog, 
                             QMessageBox, QLineEdit, QPlainTextEdit)
from PyQt5.QtCore import Qt
from PyQt5 import uic

class WhatsAppAuto(QDialog):
    def __init__(self):
        super().__init__()
        # Load the UI file
        uic.loadUi('whatsapp-auto.ui', self)
        
        # Connect buttons to new integrated functionality
        self.pushButton.clicked.connect(self.open_text_editor)                         # Text button
        self.pushButton_2.clicked.connect(self.open_image_manager)                     # Image button  
        self.pushButton_3.clicked.connect(self.run_whatsapp_script)                    # Start button
        self.pushButton_4.clicked.connect(self.open_phone_number_editor)               # Phone Number button
        self.pushButton_5.clicked.connect(self.open_exclude_words_editor)              # Text to Exclude button

    def open_text_editor(self):
        """Open text editor dialog for description.txt"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Message Text Editor")
        dialog.setFixedSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Label
        label = QLabel("Enter the message text to send:")
        layout.addWidget(label)
        
        # Text editor
        text_edit = QPlainTextEdit()
        text_edit.setPlainText(self.load_description_file())
        layout.addWidget(text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        
        save_btn.clicked.connect(lambda: self.save_description_file(text_edit.toPlainText(), dialog))
        cancel_btn.clicked.connect(dialog.close)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def load_description_file(self):
        """Load content from description.txt"""
        try:
            with open('TXT File/description.txt', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def save_description_file(self, content, dialog):
        """Save content to description.txt"""
        try:
            with open('TXT File/description.txt', 'w', encoding='utf-8') as f:
                f.write(content)
            dialog.close()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save file: {str(e)}")

    def open_phone_number_editor(self):
        """Open phone number editor dialog for phone_number.txt"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Phone Number Editor")
        dialog.setFixedSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Label
        label = QLabel("Enter phone numbers (one per line):")
        layout.addWidget(label)
        
        # Text editor
        text_edit = QPlainTextEdit()
        text_edit.setPlainText(self.load_phone_numbers())
        layout.addWidget(text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cleanup_btn = QPushButton("Clean Numbers")
        cancel_btn = QPushButton("Cancel")
        
        save_btn.clicked.connect(lambda: self.save_phone_numbers(text_edit.toPlainText(), dialog))
        cleanup_btn.clicked.connect(lambda: self.cleanup_phone_numbers(text_edit))
        cancel_btn.clicked.connect(dialog.close)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cleanup_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def load_phone_numbers(self):
        """Load phone numbers from phone_number.txt"""
        try:
            with open('TXT File/phone_number.txt', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def cleanup_phone_numbers(self, text_edit):
        """Clean phone numbers by removing +, spaces, and dashes"""
        import re
        current_text = text_edit.toPlainText()
        lines = current_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            if line.strip():
                # Remove +, spaces, dashes, and any other non-digit characters except newlines
                cleaned_number = re.sub(r'[^\d]', '', line.strip())
                if cleaned_number:  # Only add if there are digits left
                    cleaned_lines.append(cleaned_number)
        
        # Update the text editor with cleaned numbers
        cleaned_text = '\n'.join(cleaned_lines)
        text_edit.setPlainText(cleaned_text)
        
        # Show count of cleaned numbers
        count = len(cleaned_lines)
        print(f"✅ Cleaned {count} phone numbers (removed +, spaces, dashes)")

    def save_phone_numbers(self, content, dialog):
        """Save phone numbers to phone_number.txt"""
        try:
            with open('TXT File/phone_number.txt', 'w', encoding='utf-8') as f:
                f.write(content)
            dialog.close()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save file: {str(e)}")

    def open_image_manager(self):
        """Open image manager for IMAGE-TO-SEND folder"""
        folder_name = "IMAGE-TO-SEND"
        
        # Create folder if it doesn't exist
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        
        # Show file dialog to select image
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            None, 
            "Select Image to Send", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        
        if file_path:
            # Clear existing images in folder
            import glob
            existing_files = glob.glob(os.path.join(folder_name, "*"))
            for file in existing_files:
                try:
                    os.remove(file)
                except:
                    pass
            
            # Copy selected image to folder
            import shutil
            filename = os.path.basename(file_path)
            destination = os.path.join(folder_name, filename)
            shutil.copy2(file_path, destination)

    def run_whatsapp_script(self):
        """Run the WhatsApp automation script"""
        try:
            # Check if required files exist
            if not os.path.exists('TXT File/description.txt'):
                QMessageBox.warning(None, "Warning", "description.txt not found! Please add message text first.")
                return
            
            if not os.path.exists('TXT File/phone_number.txt'):
                QMessageBox.warning(None, "Warning", "phone_number.txt not found! Please add phone numbers first.")
                return
            
            # Run the WhatsApp script using subprocess for better control
            import subprocess
            try:
                # Use system Python (works better than Anaconda Python)
                script_path = os.path.abspath('whatsapp-phone-number.py')
                python_path = '/usr/local/bin/python3'
                
                # Use osascript to run the script in a new Terminal window
                applescript = f'''
                tell application "Terminal"
                    activate
                    do script "cd '{os.getcwd()}' && {python_path} '{script_path}'"
                end tell
                '''
                
                subprocess.run(['osascript', '-e', applescript])
                print("WhatsApp automation script started in new Terminal window!")
                
            except Exception as fallback_error:
                try:
                    # Fallback: try other Python paths
                    for python_cmd in ['python3', 'python', '/opt/anaconda3/bin/python']:
                        try:
                            subprocess.Popen([python_cmd, 'whatsapp-phone-number.py'])
                            print(f"WhatsApp automation script started with {python_cmd}!")
                            break
                        except FileNotFoundError:
                            continue
                    else:
                        QMessageBox.critical(None, "Error", "Python not found! Please install Python.")
                except Exception as e:
                    QMessageBox.critical(None, "Error", f"Failed to start script: {str(e)}")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error running script: {str(e)}")

    def open_exclude_words_editor(self):
        """Open exclude words editor dialog for configuring words to exclude"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Text to Exclude Editor")
        dialog.setFixedSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Label with instructions
        label = QLabel("Enter words/phrases to exclude when clicking names (one per line):")
        label2 = QLabel("Example: NepalWin, NPW, Blocked, Admin, etc.")
        label2.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(label)
        layout.addWidget(label2)
        
        # Text editor
        text_edit = QPlainTextEdit()
        text_edit.setPlainText(self.load_exclude_words())
        layout.addWidget(text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Reset to Default")
        close_btn = QPushButton("Cancel")
        
        save_btn.clicked.connect(lambda: self.save_exclude_words(text_edit.toPlainText(), dialog))
        cancel_btn.clicked.connect(lambda: text_edit.setPlainText(self.get_default_exclude_words()))
        close_btn.clicked.connect(dialog.close)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def load_exclude_words(self):
        """Load exclude words from exclude_words.txt"""
        try:
            with open('TXT File/exclude_words.txt', 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            # Return default exclude words if file doesn't exist
            default_words = self.get_default_exclude_words()
            self.save_exclude_words_to_file(default_words)
            return default_words

    def get_default_exclude_words(self):
        """Get default exclude words"""
        return "NepalWin\nNPW\nBlocked"

    def save_exclude_words(self, content, dialog):
        """Save exclude words to exclude_words.txt"""
        try:
            self.save_exclude_words_to_file(content)
            dialog.close()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save file: {str(e)}")

    def save_exclude_words_to_file(self, content):
        """Save exclude words to file"""
        with open('TXT File/exclude_words.txt', 'w', encoding='utf-8') as f:
            f.write(content)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WhatsAppAuto()
    window.show()
    sys.exit(app.exec_())