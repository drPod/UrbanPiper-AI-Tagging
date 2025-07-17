import os

# Directory containing your files
directory = "transcripts"

# Loop through all files in the directory
for filename in os.listdir(directory):
    # Get the full path
    file_path = os.path.join(directory, filename)

    # Check if it's a file (not a directory)
    if os.path.isfile(file_path):
        # Check if it doesn't already have a .txt extension
        if not filename.endswith(".txt"):
            # Rename the file with .txt extension
            new_file_path = file_path + ".txt"
            os.rename(file_path, new_file_path)
            print(f"Renamed: {filename} to {filename}.txt")
