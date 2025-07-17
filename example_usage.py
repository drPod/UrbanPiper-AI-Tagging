#!/usr/bin/env python3
"""
Example usage of the TranscriptTagAnalyzer
"""

from transcript_tag_analyzer import TranscriptTagAnalyzer
import os


# Example usage without command line arguments
def example_usage():
    # Set your OpenAI API key
    # Option 1: Set as environment variable
    # os.environ['OPENAI_API_KEY'] = 'your-api-key-here'

    # Option 2: Pass directly to analyzer
    # analyzer = TranscriptTagAnalyzer(openai_api_key='your-api-key-here')

    # Initialize analyzer (uses OPENAI_API_KEY env var)
    analyzer = TranscriptTagAnalyzer()

    # Directory containing your transcript .txt files
    transcript_directory = "transcripts"  # Change this to your directory

    # Read transcripts
    transcripts = analyzer.read_transcript_files(transcript_directory)

    if transcripts:
        # Analyze transcripts
        results = analyzer.generate_comprehensive_tag_suggestions(transcripts)

        # Save results
        analyzer.save_results(results, "my_tag_analysis.json")

        # Print summary
        analyzer.print_summary(results)
    else:
        print("No transcripts found!")


if __name__ == "__main__":
    example_usage()
