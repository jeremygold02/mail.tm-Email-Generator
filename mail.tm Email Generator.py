import os
import contextlib
import nltk
import random
import string
import requests
from nltk.corpus import wordnet as wn
from nltk.data import find
from datetime import datetime
import pytz
import textwrap

# File to store generated emails and passwords
EMAIL_FILE = "emails.txt"

"""
----------------------------------------------------------------------------------------------
GENERATING EMAIL
----------------------------------------------------------------------------------------------
"""

def ensure_nltk_resources():
    # Check if 'wordnet' and 'omw-1.4' are already downloaded
    wordnet_available = True
    omw_available = True
    
    try:
        find('corpora/wordnet.zip')
    except LookupError:
        wordnet_available = False

    try:
        find('corpora/omw-1.4.zip')
    except LookupError:
        omw_available = False

    # Download resources if they are not available
    if not wordnet_available or not omw_available:
        print("Downloading NLTK resources...")
        
        with open(os.devnull, 'w') as fnull:
            with contextlib.redirect_stdout(fnull):
                if not wordnet_available:
                    nltk.download('wordnet', quiet=True)
                if not omw_available:
                    nltk.download('omw-1.4', quiet=True)
                    
        print("Download complete.")
    else:
        print("NLTK resources are up-to-date.")

# Ensure NLTK resources are downloaded silently
ensure_nltk_resources()

def is_valid_word(word):
    """Check if the word is valid: less than 10 characters and no hyphens or underscores."""
    return len(word) < 10 and '-' not in word and '_' not in word

# Get a random adjective from the WordNet corpus
def get_random_adjective():
    while True:
        adjectives = list(wn.all_synsets('a'))  # 'a' is for adjectives
        random_adj = random.choice(adjectives)
        adjective = random_adj.lemmas()[0].name()  # Get a random adjective's lemma (root word)
        if is_valid_word(adjective):
            return adjective

# Get a random noun from the WordNet corpus
def get_random_noun():
    while True:
        nouns = list(wn.all_synsets('n'))  # 'n' is for nouns
        random_noun = random.choice(nouns)
        noun = random_noun.lemmas()[0].name()  # Get a random noun's lemma (root word)
        if is_valid_word(noun):
            return noun

# Generate a random email username in the format {adjective}{noun}{numbers}
def generate_email_username():
    adjective = get_random_adjective()
    noun = get_random_noun()
    
    # Generate a list of 3 unique digits
    numbers = ''.join(random.sample(string.digits, 3))  # random.sample ensures unique digits

    return f"{adjective}{noun}"

# Generate a random 16-character password with lowercase, uppercase, numbers, and symbols
def generate_password():
    length = 20

    # Define the character sets you want to include
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*()-=_+[]{}"  # Your specific set of symbols

    # Ensure at least 4 symbols in the password
    chosen_symbols = random.sample(symbols, 4)

    # Fill the remaining characters with a mix of the other sets
    remaining_length = length - len(chosen_symbols)
    all_characters = lowercase + uppercase + digits

    # Generate the rest of the password ensuring no repeats
    remaining_characters = random.sample(all_characters, remaining_length)

    # Combine and shuffle the password characters
    password_characters = chosen_symbols + remaining_characters
    random.shuffle(password_characters)  # Shuffle to avoid predictable sequences

    # Join characters to form the final password
    password = ''.join(password_characters)

    return password

def save_email_and_password(email, password):
    note = input("Enter a note for this email address: ")
    print()
    if note:
        with open(EMAIL_FILE, "a") as file:
            file.write(f"{email}:{password}|{note}\n")
    else:
        with open(EMAIL_FILE, "a") as file:
            file.write(f"{email}:{password}\n")

def create_email():
    custom_username = input("Enter a username, or leave blank to randomly generate: ")
    if custom_username:
        username = custom_username
    else:
        username = generate_email_username()
    password = generate_password()
    
    # Fetch the valid domain from mail.tm API
    session = requests.Session()
    domain_response = session.get('https://api.mail.tm/domains')
    domain_response.raise_for_status()
    domains = domain_response.json()['hydra:member']

    # Use the first domain in the list
    domain = domains[0]['domain']

    # Mail.tm API endpoint for email creation
    url = "https://api.mail.tm/accounts"
    payload = {
        "address": f"{username}@{domain}",  # Use the fetched domain
        "password": password
    }

    response = session.post(url, json=payload)

    if response.status_code == 201:
        # Email created successfully
        email_data = response.json()
        email = email_data['address']
        print(f"Generated Email: {email}")
        print(f"Password: {password}")
        save_email_and_password(email, password)
    else:
        print("Failed to create email. Response:", response.json())

"""
----------------------------------------------------------------------------------------------
CHECKING INBOX
----------------------------------------------------------------------------------------------
"""

def check_inbox(session):
    inbox_url = 'https://api.mail.tm/messages'
    
    # Check for messages in the inbox
    inbox_response = session.get(inbox_url)
    inbox_response.raise_for_status()
    
    messages = inbox_response.json().get('hydra:member', [])
    
    if messages:
        print(f"You have {len(messages)} message(s):\n")
        for i, msg in enumerate(messages, start=1):
            print(f"[{i}] {msg['from']['address']}: {msg['subject']}")
        return messages
    else:
        print("No emails.\n")
        return []

def view_email(session, email_id):
    email_url = f'https://api.mail.tm/messages/{email_id}'
    
    # Fetch the email content
    email_response = session.get(email_url)
    email_response.raise_for_status()
    email_content = email_response.json()
    
    print(f"From: {email_content['from']['address']}")
    print(f"Subject: {email_content['subject']}")
    
    # Check for possible keys for email content
    content = email_content.get('content') or email_content.get('text') or email_content.get('body')
    
    if content:
        print(f"Content: {content}")
    else:
        print("No content available for this email.")

def choose_email_from_file():
    print("--- Saved Emails ---")
    with open(EMAIL_FILE, "r") as file:
        emails = file.readlines()
        for i, line in enumerate(emails, start=1):
            parts = line.strip().split(':', 1)  # Split only at the first colon
            if len(parts) > 1:
                password_note_part = parts[1].split('|', 1)
                note = password_note_part[1].strip() if len(password_note_part) > 1 else ""
                email = parts[0].strip()  # Get only the email part
                print(f"[{i}] {email} | {note}")

    choice = input("Select an email to check (or type 'b' to go back): ").strip()
    if choice.lower() == 'b':
        return None

    try:
        idx = int(choice) - 1
        selected_line = emails[idx].strip()
        email = selected_line.split(':', 1)[0]  # Get email before the first colon
        return email
    except (ValueError, IndexError):
        print("Please enter a valid number.")
        return None

def check_email_inbox():
    email = choose_email_from_file()
    print()
    if email:
        password = None
        # Load the saved password from the file
        with open(EMAIL_FILE, "r") as file:
            for line in file:
                if email in line:
                    # Split at the first colon and strip whitespace
                    password_note_part = line.split(":", 1)[1].strip()
                    # Take the password part before any pipe character
                    password = password_note_part.split('|', 1)[0].strip()
                    break
        if password:
            # Create a new session to check the inbox of the saved email
            session = requests.Session()
            login_data = {"address": email, "password": password}
            login_response = session.post('https://api.mail.tm/token', json=login_data)
            login_response.raise_for_status()
            token_info = login_response.json()
            session.headers.update({"Authorization": f"Bearer {token_info['token']}"})

            print(f"Checking inbox for {email}...\n")
            messages = check_inbox(session)
            if messages:
                while True:
                    email_num = input("\nEnter the number of the email to view (or type 'b' to go back): ").strip()
                    if email_num.lower() == 'b':
                        break
                    try:
                        email_id = messages[int(email_num) - 1]['id']
                        print()
                        view_email(session, email_id)
                    except (ValueError, IndexError):
                        print("Please enter a valid number.")
                        continue

"""
----------------------------------------------------------------------------------------------
DELETING EMAILS
----------------------------------------------------------------------------------------------
"""

def delete_saved_email():
    view_saved_emails(show_passwords=False, show_details=False)
    with open(EMAIL_FILE, "r") as file:
        emails = file.readlines()
    choice = input("Select an email to delete (or type 'b' to go back): ").strip()
    if choice.lower() == 'b':
        return

    try:
        idx = int(choice) - 1
        selected_line = emails[idx].strip()

        # Extract email and password properly by splitting at colon and pipe
        email = selected_line.split(':', 1)[0].strip()  # Email before the first colon
        password = selected_line.split(':', 1)[1].split('|', 1)[0].strip()  # Password between colon and pipe

        confirmation = input(f"Are you sure you want to delete the email '{email}'? (y/n): ").strip().lower()
        if confirmation == 'y':
            session = requests.Session()
            login_data = {"address": email, "password": password}
            login_response = session.post('https://api.mail.tm/token', json=login_data)
            login_response.raise_for_status()  # This will raise an error if authentication fails
            token_info = login_response.json()
            session.headers.update({"Authorization": f"Bearer {token_info['token']}"})

            # Retrieve account ID using the /me endpoint
            account_response = session.get('https://api.mail.tm/me')
            account_response.raise_for_status()  # Raise an error if the request fails

            account_data = account_response.json()
            account_id = account_data['id']  # Get the account ID from the response

            # Send the delete request
            delete_url = f'https://api.mail.tm/accounts/{account_id}'
            delete_response = session.delete(delete_url)

            if delete_response.status_code == 204:
                print(f"Successfully deleted email: {email}")
                # Remove the email from the text file
                with open(EMAIL_FILE, "w") as file:
                    for line in emails:
                        if email not in line:  # Write back all lines except the deleted one
                            file.write(line)
            else:
                print("Failed to delete email. Response:", delete_response.json())
        else:
            print("Email deletion canceled.")
    except (ValueError, IndexError):
        print("Please enter a valid number.")
    except Exception as e:
        print(f"Error: {str(e)}")

"""
----------------------------------------------------------------------------------------------
LISTING EMAILS
----------------------------------------------------------------------------------------------
"""

def format_datetime(dt_string):
    # Parse the datetime string
    dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
    
    # Convert to Toronto time (UTC-5)
    toronto_timezone = pytz.timezone('America/Toronto')
    
    # Set the UTC timezone to the parsed datetime
    dt_utc = dt.replace(tzinfo=pytz.utc)
    
    # Convert UTC time to Toronto time
    toronto_time = dt_utc.astimezone(toronto_timezone)

    # Format the datetime in a more readable way
    return toronto_time.strftime('%B %d, %Y, %I:%M:%S %p')  # Example: "April 1, 2022, 12:00:00 AM"

def view_saved_emails(show_passwords=True, show_details=True):
    print("--- Saved Emails ---")
    
    with open(EMAIL_FILE, "r") as file:
        emails = file.readlines()
    if not emails:  # Check if there are no emails in the file
        print("No saved emails available.")
        return
    
    for i, line in enumerate(emails, start=1):
        parts = line.strip().split(':', 1)  # Split only at the first colon
        if len(parts) > 1:
            # Extract the password and note if present, otherwise keep them empty
            password_note_part = parts[1].split('|', 1)
            password = password_note_part[0].strip()  # The password is before the pipe
            note = password_note_part[1].strip() if len(password_note_part) > 1 else ""

            email = parts[0].strip()  # Get only the email part

            # Build the output
            output = f"[{i}] {email}"
            if show_passwords:
                output += f":{password}"  # Add the password if show_passwords is True
            if note:
                output += f" | {note}"  # Add the note if it exists

            print(output)

    # If show_details is True, ask the user for more details
    if show_details:
        choice = input("Enter an number to see more info about the email ('b' to go back): ").strip()
        
        if choice.lower() != 'b':
            try:
                idx = int(choice) - 1  # Convert the input to an index (1-based to 0-based)

                if idx < 0 or idx >= len(emails):
                    raise IndexError  # Raise an error if the index is out of range

                selected_line = emails[idx].strip()
                
                # Here, we handle cases where the line might not match expected format
                email_part = selected_line.split(':', 1)[0].strip()
                password_part = selected_line.split(':', 1)[1].split('|')[0].strip() if ':' in selected_line and '|' in selected_line else None

                if not email_part or not password_part:
                    raise ValueError("Invalid format in emails.txt")

                # Make the /me request to get details
                session = requests.Session()
                login_data = {"address": email_part, "password": password_part}
                login_response = session.post('https://api.mail.tm/token', json=login_data)
                login_response.raise_for_status()  # Raise an error if authentication fails
                token_info = login_response.json()
                session.headers.update({"Authorization": f"Bearer {token_info['token']}"})

                # Retrieve account information from /me endpoint
                account_response = session.get('https://api.mail.tm/me')
                account_response.raise_for_status()
                account_data = account_response.json()

                # Format the /me response nicely
                formatted_info = textwrap.dedent(f"""
                    --- Email Details ---
                    Email Address: {account_data['address']}
                    Account ID: {account_data['id']}
                    Quota: {account_data['quota']} bytes
                    Used: {account_data['used']} bytes
                    Created At: {format_datetime(account_data['createdAt'])}
                    Updated At: {format_datetime(account_data['updatedAt'])}
                """)

                print(formatted_info)

            except ValueError as ve:
                print(f"Value Error: {ve}. Please enter a valid number.")
            except IndexError:
                print("The number you entered is out of range.")
            except Exception as e:
                print(f"Error retrieving details: {str(e)}")

"""
----------------------------------------------------------------------------------------------
MAIN FUNCTION
----------------------------------------------------------------------------------------------
"""

def display_menu():
    print("\n--- Mail.tm Email Generator ---")
    print("[1] Generate New Email")
    print("[2] Check Inbox of a Saved Email")
    print("[3] Delete a Saved Email")
    print("[4] View Saved Emails")

def main():
    while True:
        display_menu()
        choice = input("Select an option: ")
        print()

        if choice == '1':
            create_email()
        elif choice == '2':
            check_email_inbox()
        elif choice == '3':
            delete_saved_email()
            pass
        elif choice == '4':
            view_saved_emails()
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
