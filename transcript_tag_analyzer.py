import os
import glob
from openai import OpenAI
from typing import List, Dict, Set
import json
from collections import Counter
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class TranscriptTagAnalyzer:
    def __init__(self, openai_api_key: str = None):
        """
        Initialize the transcript analyzer with OpenAI API key.
        If no key provided, will look for OPENAI_API_KEY environment variable.
        """
        if openai_api_key:
            self.client = OpenAI(api_key=openai_api_key)
        else:
            self.client = OpenAI()  # Uses OPENAI_API_KEY env var
    
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
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read().strip()
                    if content:
                        transcripts.append({
                            'filename': os.path.basename(file_path),
                            'content': content
                        })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        print(f"Successfully loaded {len(transcripts)} transcript files")
        return transcripts
    
    def analyze_transcript_for_tags(self, transcript: str) -> Dict[str, any]:
        """
        Use OpenAI to analyze a single transcript and suggest relevant tags with explanations.
        """
        prompt = f"""
        Analyze this restaurant phone order transcript from the restaurant owner's perspective and suggest relevant tags that would help them understand the call quality and customer experience.

        Focus on tags that capture customer experience and call quality, such as:
        - Positive indicators: happy, smooth, quick call, menu explained, questions answered, high order value, upselling
        - Negative indicators: annoyed, repetitions, interruptions, missed answers, missing items, no upselling, rejected upsell, order corrections
        - Special cases: human requested (when AI directs call to human agent)

        Example tags to consider: [happy, smooth, quick call, menu explained, questions answered, high order value, upselling, annoyed, repetitions, interruptions, human requested, missed answers, missing items, no upselling, rejected upsell, order corrections]

        Transcript:
        {transcript}

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
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            return result
            
        except Exception as e:
            print(f"Error analyzing transcript: {e}")
            return {"tags": [], "explanations": {}}
    
    def generate_comprehensive_tag_suggestions(self, transcripts: List[Dict[str, str]]) -> Dict[str, any]:
        """
        Analyze all transcripts and generate comprehensive tag suggestions.
        """
        print("Analyzing transcripts to generate tag suggestions...")
        
        all_tags = []
        transcript_analysis = {}
        
        for i, transcript in enumerate(transcripts, 1):
            print(f"Processing transcript {i}/{len(transcripts)}: {transcript['filename']}")
            
            analysis = self.analyze_transcript_for_tags(transcript['content'])
            tags = analysis.get('tags', [])
            explanations = analysis.get('explanations', {})
            
            all_tags.extend(tags)
            transcript_analysis[transcript['filename']] = {
                'tags': tags,
                'explanations': explanations
            }
        
        # Count tag frequency
        tag_frequency = Counter(all_tags)
        
        # Generate final tag recommendations
        final_recommendations = self.generate_final_recommendations(all_tags, tag_frequency)
        
        return {
            'individual_transcript_analysis': transcript_analysis,
            'tag_frequency': dict(tag_frequency),
            'recommended_tags': final_recommendations,
            'total_transcripts_analyzed': len(transcripts),
            'total_tags_generated': len(all_tags),
            'unique_tags': len(set(all_tags))
        }
    
    def generate_final_recommendations(self, all_tags: List[str], tag_frequency: Counter) -> Dict[str, List[str]]:
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
                temperature=0.3
            )
            
            recommendations = json.loads(response.choices[0].message.content.strip())
            return recommendations
            
        except Exception as e:
            print(f"Error generating final recommendations: {e}")
            # Fallback to simple categorization
            return {
                "Most_Common_Tags": most_common_tags[:10]
            }
    
    def save_results(self, results: Dict[str, any], output_file: str = "tag_analysis_results.json"):
        """
        Save the analysis results to a JSON file.
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_file}")
    
    def print_summary(self, results: Dict[str, any]):
        """
        Print a summary of the analysis results.
        """
        print("\n" + "="*60)
        print("TRANSCRIPT TAG ANALYSIS SUMMARY")
        print("="*60)
        
        print(f"Total transcripts analyzed: {results['total_transcripts_analyzed']}")
        print(f"Total tags generated: {results['total_tags_generated']}")
        print(f"Unique tags found: {results['unique_tags']}")
        
        print("\nRECOMMENDED TAGS BY CATEGORY:")
        print("-" * 40)
        
        for category, tags in results['recommended_tags'].items():
            print(f"\n{category.replace('_', ' ').title()}:")
            for tag in tags:
                print(f"  • {tag}")
        
        print("\nTOP 10 MOST FREQUENT TAGS:")
        print("-" * 30)
        
        sorted_tags = sorted(results['tag_frequency'].items(), key=lambda x: x[1], reverse=True)
        for tag, count in sorted_tags[:10]:
            print(f"  {tag}: {count} occurrences")
        
        print("\nINDIVIDUAL TRANSCRIPT ANALYSIS:")
        print("-" * 40)
        
        for filename, analysis in results['individual_transcript_analysis'].items():
            print(f"\n{filename}:")
            print(f"  Tags: {', '.join(analysis['tags'])}")
            print("  Explanations:")
            for tag, explanation in analysis['explanations'].items():
                print(f"    • {tag}: {explanation}")

def main():
    parser = argparse.ArgumentParser(description='Analyze restaurant phone transcripts to generate tagging suggestions')
    parser.add_argument('transcript_directory', help='Directory containing transcript .txt files')
    parser.add_argument('--output', '-o', default='tag_analysis_results.json', help='Output file for results')
    parser.add_argument('--api-key', help='OpenAI API key (or set OPENAI_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Check if transcript directory exists
    if not os.path.exists(args.transcript_directory):
        print(f"Error: Directory '{args.transcript_directory}' does not exist.")
        return
    
    try:
        # Initialize analyzer
        analyzer = TranscriptTagAnalyzer(openai_api_key=args.api_key)
        
        # Read transcripts
        transcripts = analyzer.read_transcript_files(args.transcript_directory)
        
        if not transcripts:
            print("No transcripts found to analyze.")
            return
        
        # Analyze transcripts
        results = analyzer.generate_comprehensive_tag_suggestions(transcripts)
        
        # Save and display results
        analyzer.save_results(results, args.output)
        analyzer.print_summary(results)
        
    except Exception as e:
        print(f"Error during analysis: {e}")

if __name__ == "__main__":
    main()