#!/usr/bin/env python3
"""
Test script to fetch a single transcript from Quibble AI platform
"""

import os
import sys
from fetch_transcripts import QuibbleTranscriptFetcher

def main():
    # Get authentication from environment variables
    auth_token = os.getenv('QUIBBLE_AUTH_TOKEN')
    cookie = os.getenv('QUIBBLE_COOKIE')
    
    # Test call ID (from the example you provided)
    test_call_id = "687a7f56a1698f750734da54"
    
    # Initialize the fetcher
    fetcher = QuibbleTranscriptFetcher(auth_token=auth_token, cookie=cookie)
    
    print(f"Testing with call ID: {test_call_id}")
    print(f"API URL: {fetcher.api_base_url}/api/v1/history/chat?chatId={test_call_id}")
    
    # Fetch the transcript
    transcript = fetcher.fetch_transcript(test_call_id)
    
    if transcript:
        print("\n" + "="*50)
        print("SUCCESS! Transcript fetched:")
        print("="*50)
        print(transcript[:500] + "..." if len(transcript) > 500 else transcript)
        
        # Save it
        fetcher.save_transcript(test_call_id, transcript)
        
    else:
        print("\nFailed to fetch transcript. Check your authentication credentials.")

if __name__ == "__main__":
    main()