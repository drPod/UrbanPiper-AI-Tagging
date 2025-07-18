# UrbanPiper AI Tagging System

This repository contains tools for analyzing restaurant phone call transcripts and generating AI-powered tags to help restaurant owners understand call quality and customer experience.

## Overview

The system consists of two main components:
1. **Transcript Fetcher**: Downloads call transcripts from CSV data
2. **Tag Analyzer**: Uses OpenAI to analyze transcripts and generate relevant tags

## Setup

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your OpenAI API key:
```bash
cp .env.example .env
# Edit .env with your API key
```

Or export directly:
```bash
export OPENAI_API_KEY="your_api_key_here"
```

## Usage Workflow

### Step 1: Update Call Data

When new calls are available, update the CSV file with the latest call data:
- Replace or update `calls-06-18-2025-to-07-18-2025.csv` with your new call data
- The CSV should contain call IDs and relevant metadata

### Step 2: Fetch Transcripts

Run the transcript fetcher to download transcripts for new calls:

```bash
python fetch_transcripts.py
```

This will:
- Read the CSV file for call IDs
- Download transcripts to the `transcripts/` directory
- Save each transcript as a `.txt` file named by call ID

### Step 3: Analyze Transcripts and Generate Tags

Run the tag analyzer to process transcripts and generate tags:

```bash
python transcript_tag_analyzer.py transcripts/
```

#### Basic Usage Options:

```bash
# Basic analysis with default settings
python transcript_tag_analyzer.py transcripts/

# Custom output file
python transcript_tag_analyzer.py transcripts/ --output my_analysis.json

# Faster processing with larger batches and more workers
python transcript_tag_analyzer.py transcripts/ --batch-size 20 --max-workers 10

# Resume from previous run if interrupted
python transcript_tag_analyzer.py transcripts/ --resume
```

#### Advanced Options:

- `--batch-size` / `-b`: Number of transcripts per batch (default: 10)
- `--max-workers` / `-w`: Concurrent API calls (default: 5)
- `--resume` / `-r`: Resume from existing results
- `--output` / `-o`: Output file name (default: tag_analysis_results.json)

## Output

The tag analyzer generates a comprehensive JSON file containing:

- **Individual transcript analysis**: Tags and explanations for each call
- **Tag frequency**: How often each tag appears across all calls
- **Recommended tags**: Categorized suggestions for restaurant tagging
- **Summary statistics**: Total calls analyzed, tags generated, etc.

### Example Output Structure:

```json
{
  "individual_transcript_analysis": {
    "call_id.txt": {
      "tags": ["happy", "smooth", "high order value"],
      "explanations": {
        "happy": "Customer expressed satisfaction with service",
        "smooth": "Call proceeded without interruptions",
        "high order value": "Order total was above average"
      }
    }
  },
  "tag_frequency": {
    "happy": 45,
    "smooth": 38,
    "repetitions": 12
  },
  "recommended_tags": {
    "Positive_Experience": ["happy", "smooth", "quick call"],
    "Negative_Experience": ["annoyed", "repetitions", "interruptions"],
    "Order_Quality": ["high order value", "upselling"],
    "Special_Cases": ["human requested", "missing items"]
  }
}
```

## Performance Features

- **Batch Processing**: Processes transcripts in batches to save progress incrementally
- **Parallel Processing**: Uses multiple threads for concurrent API calls
- **Resume Capability**: Can continue from where it left off if interrupted
- **Progress Tracking**: Shows detailed progress for each batch and transcript

## Files

- `fetch_transcripts.py`: Downloads transcripts from call data
- `transcript_tag_analyzer.py`: Main analysis tool
- `test_single_transcript.py`: Test tool for single transcript analysis
- `example_usage.py`: Example usage patterns
- `requirements.txt`: Python dependencies
- `transcripts/`: Directory containing transcript files
- `*.json`: Analysis results and tag suggestions

## Troubleshooting

- **API Rate Limits**: Reduce `--max-workers` if hitting OpenAI rate limits
- **Memory Issues**: Reduce `--batch-size` for large datasets
- **Interrupted Processing**: Use `--resume` to continue from where you left off
- **Missing Transcripts**: Ensure CSV file is updated and `fetch_transcripts.py` ran successfully

## Example Workflow

```bash
# 1. Update your CSV file with new call data
# 2. Fetch new transcripts
python fetch_transcripts.py

# 3. Analyze transcripts with optimized settings
python transcript_tag_analyzer.py transcripts/ --batch-size 15 --max-workers 8 --output latest_analysis.json

# 4. If interrupted, resume processing
python transcript_tag_analyzer.py transcripts/ --resume --output latest_analysis.json
```

The system will generate comprehensive tag suggestions to help restaurant owners understand their call quality patterns and customer experience trends.
