#!/usr/bin/env python3
"""
Script to fetch transcripts from Quibble AI platform using call IDs from CSV file

AUTHENTICATION REQUIRED:
To use this script, you need to get your authentication token from the Quibble platform:

1. Login to https://platform.quibbleai.io
2. Open browser developer tools (F12)
3. Go to Network tab
4. Make a request to the call logs or chat history
5. Find the Authorization header or cookie values
6. Set them in the environment variables below or in a .env file

Example:
export QUIBBLE_AUTH_TOKEN="your_auth_token_here"
export QUIBBLE_COOKIE="your_cookie_here"
"""

import csv
import requests
import json
import os
import time
from pathlib import Path

class QuibbleTranscriptFetcher:
    def __init__(self, api_base_url="https://prod.quibbleai.io:3000", auth_token=None, cookie=None):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.transcripts_dir = Path("transcripts")
        self.transcripts_dir.mkdir(exist_ok=True)
        
        # Set up authentication
        if auth_token:
            self.session.headers.update({'Authorization': f'Bearer {auth_token}'})
        elif cookie:
            self.session.headers.update({'Cookie': cookie})
        else:
            print("WARNING: No authentication provided. You may get 401 errors.")
            print("Please set QUIBBLE_AUTH_TOKEN or QUIBBLE_COOKIE environment variables.")
        
    def fetch_transcript(self, call_id):
        """Fetch transcript for a specific call ID using the API"""
        try:
            # API endpoint for fetching chat history
            url = f"{self.api_base_url}/api/v1/history/chat?chatId={call_id}"
            
            # Add headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
            
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'chat' in data and 'chat' in data['chat']:
                    return self.format_transcript(data['chat'], call_id)
                else:
                    print(f"No chat data found for call ID: {call_id}")
                    return None
                    
            else:
                print(f"Failed to fetch call {call_id}: HTTP {response.status_code}")
                if response.status_code == 404:
                    print(f"Call {call_id} not found")
                return None
                
        except Exception as e:
            print(f"Error fetching transcript for {call_id}: {str(e)}")
            return None
    
    def format_transcript(self, chat_data, call_id):
        """Format the chat data into a readable transcript"""
        transcript_lines = []
        
        # Add metadata
        transcript_lines.append(f"Call ID: {call_id}")
        transcript_lines.append(f"Agent: {chat_data.get('agentName', 'Unknown')}")
        transcript_lines.append(f"Call Type: {chat_data.get('callType', 'Unknown')}")
        transcript_lines.append(f"Start Time: {chat_data.get('callStarted', 'Unknown')}")
        transcript_lines.append(f"End Time: {chat_data.get('callEnded', 'Unknown')}")
        transcript_lines.append(f"Duration: {chat_data.get('time', 'Unknown')} seconds")
        transcript_lines.append(f"From: {chat_data.get('from', 'Unknown')}")
        transcript_lines.append(f"To: {chat_data.get('to', 'Unknown')}")
        
        if 'summary' in chat_data:
            transcript_lines.append(f"Summary: {chat_data['summary']}")
        
        transcript_lines.append("=" * 50)
        transcript_lines.append("TRANSCRIPT:")
        transcript_lines.append("=" * 50)
        
        # Process chat messages
        for message in chat_data.get('chat', []):
            role = message.get('role', 'unknown')
            content = message.get('message', '')
            timestamp = message.get('timestamp', '')
            
            # Format role name
            if role == 'assistant':
                role_name = "AI Agent"
            elif role == 'user':
                role_name = "Customer"
            else:
                role_name = role.title()
            
            # Skip system messages that are JSON objects
            if content.startswith('{') and content.endswith('}'):
                try:
                    json.loads(content)
                    continue  # Skip JSON system messages
                except json.JSONDecodeError:
                    pass  # Not JSON, include it
            
            # Add formatted message
            transcript_lines.append(f"\n[{timestamp}] {role_name}: {content}")
        
        return '\n'.join(transcript_lines)
    
    def save_transcript(self, call_id, transcript_text):
        """Save transcript to file"""
        filename = self.transcripts_dir / f"{call_id}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(transcript_text)
        
        print(f"Saved transcript for {call_id} to {filename}")
    
    def fetch_all_transcripts(self, csv_file_path):
        """Fetch all transcripts from CSV file"""
        if not os.path.exists(csv_file_path):
            print(f"CSV file not found: {csv_file_path}")
            return
        
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            call_ids = [row['callId'] for row in reader]
        
        print(f"Found {len(call_ids)} call IDs in CSV file")
        
        successful_fetches = 0
        failed_fetches = 0
        
        for i, call_id in enumerate(call_ids, 1):
            print(f"\nProcessing {i}/{len(call_ids)}: {call_id}")
            
            # Check if transcript already exists
            transcript_file = self.transcripts_dir / f"{call_id}.txt"
            if transcript_file.exists():
                print(f"Transcript already exists for {call_id}, skipping...")
                continue
            
            transcript = self.fetch_transcript(call_id)
            
            if transcript:
                self.save_transcript(call_id, transcript)
                successful_fetches += 1
            else:
                failed_fetches += 1
            
            # Add delay to avoid overwhelming the server
            time.sleep(0.5)
        
        print(f"\n" + "="*50)
        print(f"Finished fetching transcripts!")
        print(f"Successful: {successful_fetches}")
        print(f"Failed: {failed_fetches}")
        print(f"Total: {len(call_ids)}")
        print(f"Transcripts saved to: {self.transcripts_dir}")

def main():
    # Get authentication from environment variables
    auth_token = os.getenv('QUIBBLE_AUTH_TOKEN')
    cookie = os.getenv('QUIBBLE_COOKIE')
    
    # Initialize the fetcher
    fetcher = QuibbleTranscriptFetcher(auth_token=auth_token, cookie=cookie)
    
    # CSV file path
    csv_file = "calls-06-18-2025-to-07-18-2025.csv"
    
    # Check if CSV file exists
    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found!")
        print("Please make sure the CSV file is in the current directory.")
        return
    
    # Check if authentication is provided
    if not auth_token and not cookie:
        print("\nTo get authentication credentials:")
        print("1. Login to https://platform.quibbleai.io")
        print("2. Open browser developer tools (F12)")
        print("3. Go to Network tab")
        print("4. Navigate to call logs or make a request")
        print("5. Find a request to the API and copy the Authorization header or Cookie")
        print("6. Set environment variable:")
        print("   export QUIBBLE_AUTH_TOKEN='your_token_here'")
        print("   OR")
        print("   export QUIBBLE_COOKIE='your_cookie_here'")
        print("\nContinuing without authentication (may fail)...")
    
    # Fetch all transcripts
    fetcher.fetch_all_transcripts(csv_file)

if __name__ == "__main__":
    main()