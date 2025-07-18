import os
import glob
from openai import OpenAI
from typing import List, Dict, Set
import json
from collections import Counter
import argparse
from dotenv import load_dotenv
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables from .env file
load_dotenv()


class TranscriptTagAnalyzer:
    def __init__(
        self, openai_api_key: str = None, batch_size: int = 10, max_workers: int = 5
    ):
        """
        Initialize the transcript analyzer with OpenAI API key.
        If no key provided, will look for OPENAI_API_KEY environment variable.

        Args:
            openai_api_key: OpenAI API key
            batch_size: Number of transcripts to process before saving batch results
            max_workers: Maximum number of concurrent API calls
        """
        if openai_api_key:
            self.client = OpenAI(api_key=openai_api_key)
        else:
            self.client = OpenAI()  # Uses OPENAI_API_KEY env var

        self.batch_size = batch_size
        self.max_workers = max_workers
        self.results_lock = threading.Lock()

    def read_transcript_files(self, directory_path: str) -> List[Dict[str, str]]:
        """
        Read all .txt files from the specified directory and return transcript data.
        """
        transcripts = []
        txt_files = glob.glob(os.path.join(directory_path, "*.txt"))

        if not txt_files:
            print(f"No .txt files found in {directory_path}")
            return transcripts

        for file_path in txt_files:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read().strip()
                    if content:
                        transcripts.append(
                            {
                                "filename": os.path.basename(file_path),
                                "content": content,
                            }
                        )
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

        print(f"Successfully loaded {len(transcripts)} transcript files")
        return transcripts

    def analyze_transcript_for_tags(self, transcript: str) -> Dict[str, any]:
        """
        Use OpenAI to analyze a single transcript and suggest relevant tags with explanations.
        """
        prompt = f"""
            **Objective:**
            You are an AI assistant tasked with analyzing phone order transcripts for a restaurant. Your primary goal is to identify and tag calls that contain noteworthy events, either positive or negative, which would be valuable for a restaurant owner to review.

            **Core Instruction: High Conviction Tagging**
            Most calls will be routine and will not require any tags. You should **ONLY** apply a tag if you have very high confidence that the event is explicitly present and clearly demonstrated in the transcript. If a call is standard, mundane, or uneventful, you **MUST** return an empty list of tags. Do not force a tag if it doesn't clearly fit.

            **Rules:**

            1.  Read the entire transcript carefully.

            2.  Apply tags **ONLY** from the predefined list below. Do not create new tags.

            3.  For each tag you apply, provide a brief, specific explanation citing evidence from the transcript.

            4.  If no noteworthy events occur, return an empty `tags` array.

            -----

            **Predefined Tag Taxonomy:**

            **1. Positive Customer Experience**

            * `customer_happy`: Apply **only** when the customer uses explicit words of gratitude, happiness, or high praise (e.g., "This was so easy," "Thank you for all your help," "That's perfect\!").

            * `agent_upsell_success`: Apply when the agent suggests an additional item (upsell or cross-sell) and the customer agrees to add it to their order.

            **2. Negative Customer Experience**

            * `customer_annoyed`: Apply when the customer expresses clear frustration, impatience, or anger through their words (e.g., "This is taking forever," "That's not what I asked for," "I'm getting frustrated").

            * `order_correction_needed`: Apply when the agent repeats the order and the customer has to correct an item, quantity, or customization.

            * `item_unavailable`: Apply when a customer requests an item and the agent states that it is out of stock or unavailable.

            * `human_requested`: Apply **only** if the customer explicitly asks to speak to a person, manager, or human agent.

            **3. Call Quality Issues**

            * `frequent_repetitions`: Apply if the same information is repeated three or more times by either the customer or the agent due to misunderstanding.

            * `technical_issue`: Apply if there is a clear mention of a technical problem, such as the line cutting out or difficulty hearing due to static.

            -----

            **Transcript to Analyze:**

            ```
            {transcript}

            ```

            -----

            **Output Format:**
            Return your response in this JSON format:
            {{
                "tags": ["tag1", "tag2", "tag3"],
                "explanations": {{
                    "tag1": "Brief explanation of why this tag applies",
                    "tag2": "Brief explanation of why this tag applies",
                    "tag3": "Brief explanation of why this tag applies"
                }}
            }}
            """

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3,
            )

            result = json.loads(response.choices[0].message.content.strip())
            return result

        except Exception as e:
            print(f"Error analyzing transcript: {e}")
            return {"tags": [], "explanations": {}}

    def analyze_single_transcript(self, transcript: Dict[str, str]) -> Dict[str, any]:
        """
        Analyze a single transcript and return the result with filename.
        """
        analysis = self.analyze_transcript_for_tags(transcript["content"])
        return {
            "filename": transcript["filename"],
            "tags": analysis.get("tags", []),
            "explanations": analysis.get("explanations", {}),
        }

    def save_batch_results(
        self, results: Dict[str, any], output_file: str, batch_num: int = None
    ):
        """
        Save batch results to file with thread safety.
        """
        with self.results_lock:
            try:
                # Try to load existing results
                if os.path.exists(output_file):
                    with open(output_file, "r", encoding="utf-8") as f:
                        existing_results = json.load(f)
                else:
                    existing_results = {
                        "individual_transcript_analysis": {},
                        "tag_frequency": {},
                        "total_transcripts_analyzed": 0,
                        "total_tags_generated": 0,
                        "unique_tags": 0,
                        "batches_processed": 0,
                    }

                # Merge new results
                existing_results["individual_transcript_analysis"].update(
                    results["individual_transcript_analysis"]
                )

                # Update tag frequency
                for tag, count in results["tag_frequency"].items():
                    existing_results["tag_frequency"][tag] = (
                        existing_results["tag_frequency"].get(tag, 0) + count
                    )

                # Update totals
                existing_results["total_transcripts_analyzed"] += results[
                    "total_transcripts_analyzed"
                ]
                existing_results["total_tags_generated"] += results[
                    "total_tags_generated"
                ]
                existing_results["unique_tags"] = len(
                    set(existing_results["tag_frequency"].keys())
                )
                existing_results["batches_processed"] = (
                    existing_results.get("batches_processed", 0) + 1
                )

                # Save updated results
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(existing_results, f, indent=2, ensure_ascii=False)

                batch_info = f" (batch {batch_num})" if batch_num else ""
                print(f"Batch results saved to {output_file}{batch_info}")

            except Exception as e:
                print(f"Error saving batch results: {e}")

    def process_batch(
        self, batch_transcripts: List[Dict[str, str]], batch_num: int, output_file: str
    ):
        """
        Process a batch of transcripts with parallel processing.
        """
        print(
            f"Processing batch {batch_num} with {len(batch_transcripts)} transcripts..."
        )

        batch_results = {
            "individual_transcript_analysis": {},
            "tag_frequency": {},
            "total_transcripts_analyzed": 0,
            "total_tags_generated": 0,
        }

        all_tags = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_transcript = {
                executor.submit(self.analyze_single_transcript, transcript): transcript
                for transcript in batch_transcripts
            }

            # Process completed tasks
            for future in as_completed(future_to_transcript):
                transcript = future_to_transcript[future]
                try:
                    result = future.result()
                    filename = result["filename"]
                    tags = result["tags"]
                    explanations = result["explanations"]

                    # Store results
                    batch_results["individual_transcript_analysis"][filename] = {
                        "tags": tags,
                        "explanations": explanations,
                    }

                    all_tags.extend(tags)
                    batch_results["total_transcripts_analyzed"] += 1
                    batch_results["total_tags_generated"] += len(tags)

                    print(f"✓ Completed: {filename} ({len(tags)} tags)")

                except Exception as e:
                    print(f"✗ Error processing {transcript['filename']}: {e}")

        # Calculate tag frequency for this batch
        batch_results["tag_frequency"] = dict(Counter(all_tags))

        # Save batch results
        self.save_batch_results(batch_results, output_file, batch_num)

        return batch_results

    def generate_comprehensive_tag_suggestions(
        self, transcripts: List[Dict[str, str]], output_file: str = None
    ) -> Dict[str, any]:
        """
        Analyze all transcripts and generate comprehensive tag suggestions using batch processing.
        """
        print(f"Analyzing {len(transcripts)} transcripts using batch processing...")

        # Clear existing output file if it exists and we're not resuming
        if (
            output_file
            and os.path.exists(output_file)
            and not getattr(self, "_resume_mode", False)
        ):
            os.remove(output_file)
            print(f"Cleared existing output file: {output_file}")

        # Process transcripts in batches
        total_batches = (len(transcripts) + self.batch_size - 1) // self.batch_size

        for batch_num in range(1, total_batches + 1):
            start_idx = (batch_num - 1) * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(transcripts))
            batch_transcripts = transcripts[start_idx:end_idx]

            print(f"\n=== Processing Batch {batch_num}/{total_batches} ===")
            print(f"Transcripts {start_idx + 1}-{end_idx} of {len(transcripts)}")

            self.process_batch(batch_transcripts, batch_num, output_file)

        # Load final results
        if output_file and os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                final_results = json.load(f)
        else:
            final_results = {
                "individual_transcript_analysis": {},
                "tag_frequency": {},
                "total_transcripts_analyzed": 0,
                "total_tags_generated": 0,
                "unique_tags": 0,
            }

        # Generate final recommendations
        if final_results["tag_frequency"]:
            tag_frequency = Counter(final_results["tag_frequency"])
            all_tags = []
            for tag, count in tag_frequency.items():
                all_tags.extend([tag] * count)

            final_recommendations = self.generate_final_recommendations(
                all_tags, tag_frequency
            )
            final_results["recommended_tags"] = final_recommendations

        # Save final results with recommendations
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(final_results, f, indent=2, ensure_ascii=False)
            print(f"\nFinal results saved to {output_file}")

        return final_results

    def generate_final_recommendations(
        self, all_tags: List[str], tag_frequency: Counter
    ) -> Dict[str, List[str]]:
        """
        Generate final categorized tag recommendations based on all analyzed transcripts.
        """
        # Get the most common tags
        most_common_tags = [tag for tag, count in tag_frequency.most_common(20)]

        # Use LLM to categorize and refine the tags
        categorization_prompt = f"""
        Based on analysis of restaurant phone order transcripts, here are the most frequently suggested tags:
        {', '.join(most_common_tags)}

        Please organize these tags into logical categories from a restaurant owner's perspective, focusing on positive/negative customer experience indicators. 
        Create 3-4 categories and recommend the most useful tags per category.

        Format the response as JSON with this structure:
        {{
            "Positive_Experience": ["happy", "smooth", "quick call", "menu explained"],
            "Negative_Experience": ["annoyed", "repetitions", "interruptions", "missed answers"],
            "Order_Quality": ["high order value", "upselling", "order corrections"],
            "Special_Cases": ["human requested", "missing items"]
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": categorization_prompt}],
                max_tokens=400,
                temperature=0.3,
            )

            recommendations = json.loads(response.choices[0].message.content.strip())
            return recommendations

        except Exception as e:
            print(f"Error generating final recommendations: {e}")
            # Fallback to simple categorization
            return {"Most_Common_Tags": most_common_tags[:10]}

    def save_results(
        self, results: Dict[str, any], output_file: str = "tag_analysis_results.json"
    ):
        """
        Save the analysis results to a JSON file.
        """
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_file}")

    def print_summary(self, results: Dict[str, any]):
        """
        Print a summary of the analysis results.
        """
        print("\n" + "=" * 60)
        print("TRANSCRIPT TAG ANALYSIS SUMMARY")
        print("=" * 60)

        print(f"Total transcripts analyzed: {results['total_transcripts_analyzed']}")
        print(f"Total tags generated: {results['total_tags_generated']}")
        print(f"Unique tags found: {results['unique_tags']}")

        print("\nRECOMMENDED TAGS BY CATEGORY:")
        print("-" * 40)

        for category, tags in results["recommended_tags"].items():
            print(f"\n{category.replace('_', ' ').title()}:")
            for tag in tags:
                print(f"  • {tag}")

        print("\nTOP 10 MOST FREQUENT TAGS:")
        print("-" * 30)

        sorted_tags = sorted(
            results["tag_frequency"].items(), key=lambda x: x[1], reverse=True
        )
        for tag, count in sorted_tags[:10]:
            print(f"  {tag}: {count} occurrences")

        print("\nINDIVIDUAL TRANSCRIPT ANALYSIS:")
        print("-" * 40)

        for filename, analysis in results["individual_transcript_analysis"].items():
            print(f"\n{filename}:")
            print(f"  Tags: {', '.join(analysis['tags'])}")
            print("  Explanations:")
            for tag, explanation in analysis["explanations"].items():
                print(f"    • {tag}: {explanation}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze restaurant phone transcripts to generate tagging suggestions"
    )
    parser.add_argument(
        "transcript_directory", help="Directory containing transcript .txt files"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="tag_analysis_results.json",
        help="Output file for results",
    )
    parser.add_argument(
        "--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)"
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=10,
        help="Number of transcripts to process in each batch (default: 10)",
    )
    parser.add_argument(
        "--max-workers",
        "-w",
        type=int,
        default=5,
        help="Maximum number of concurrent API calls (default: 5)",
    )
    parser.add_argument(
        "--resume",
        "-r",
        action="store_true",
        help="Resume from existing output file instead of starting fresh",
    )

    args = parser.parse_args()

    # Check if transcript directory exists
    if not os.path.exists(args.transcript_directory):
        print(f"Error: Directory '{args.transcript_directory}' does not exist.")
        return

    try:
        # Initialize analyzer with batch processing parameters
        analyzer = TranscriptTagAnalyzer(
            openai_api_key=args.api_key,
            batch_size=args.batch_size,
            max_workers=args.max_workers,
        )

        # Read transcripts
        transcripts = analyzer.read_transcript_files(args.transcript_directory)

        if not transcripts:
            print("No transcripts found to analyze.")
            return

        # Handle resume functionality
        if args.resume and os.path.exists(args.output):
            print(f"Resume mode: Loading existing results from {args.output}")
            with open(args.output, "r", encoding="utf-8") as f:
                existing_results = json.load(f)

            # Filter out already processed transcripts
            processed_files = set(
                existing_results.get("individual_transcript_analysis", {}).keys()
            )
            remaining_transcripts = [
                t for t in transcripts if t["filename"] not in processed_files
            ]

            print(f"Found {len(processed_files)} already processed transcripts")
            print(f"Remaining transcripts to process: {len(remaining_transcripts)}")

            if remaining_transcripts:
                # Set resume mode flag
                analyzer._resume_mode = True
                # Process remaining transcripts
                results = analyzer.generate_comprehensive_tag_suggestions(
                    remaining_transcripts, args.output
                )
            else:
                print("All transcripts have already been processed!")
                results = existing_results
        else:
            # Process all transcripts
            results = analyzer.generate_comprehensive_tag_suggestions(
                transcripts, args.output
            )

        # Display results summary
        analyzer.print_summary(results)

    except Exception as e:
        print(f"Error during analysis: {e}")


if __name__ == "__main__":
    main()
