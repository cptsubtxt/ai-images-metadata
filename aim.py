import os
import argparse
import json
from exiftool import ExifToolHelper
import ollama

# Configuration
DEFAULT_KEYWORD_COUNT = 5
MODEL = "llava"
TONE = "witty,curios" 
TEMP = 0.5
CONFIG_FILE = "aim_config.json"

def load_config():
    """Loads configuration from a JSON file."""
    config = {"keyword_count": DEFAULT_KEYWORD_COUNT}
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        save_config(config)  # Create default config file if not exists
    return config

def save_config(config):
    """Saves configuration to a JSON file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def get_ollama_response(image_path, prompt_template, temperature=0.7):
    """Invokes Ollama to get image information with temperature control."""
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()

        response = ollama.generate(
            model=MODEL,  # or your preferred multimodal model
            prompt=prompt_template,
            images=[image_data],
            options={'temperature': temperature}, #added temperature control
        )
        return response['response'].strip()
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None

def extract_keywords(keywords_string):
    """
    Extracts keywords from a string starting with "Keywords: ".

    Args:
      keywords_string: The string containing keywords.

    Returns:
      A list of keywords.
    """
    if keywords_string.startswith("Keywords: "):
        keywords = keywords_string.replace("Keywords: ", "").strip().split(",")
        return [keyword.strip() for keyword in keywords]  # Remove extra spaces
    else:
        return []

def process_image(image_path, config):
    """Processes a single image."""

    tone = TONE.split(',')
    print(tone)
    try:
        prompt_template = f"""
        As a photojournalist analyze the following image and provide it in a {tone[0]} and {tone[1]} tone:
        - Image Headline: A short, impactful title
        - Image Description: A brief, informative summary
        - {config['keyword_count']} Image Keywords, separated by commas
        """

        ollama_response = get_ollama_response(image_path, prompt_template, TEMP)

        if ollama_response:
            print(ollama_response)
            lines = ollama_response.split('\n')
            headline = lines[0].replace("Image Headline:", "").strip()
            description = lines[1].replace("Image Description:", "").strip()
            keywords = extract_keywords(lines[2])

            # Remove quotation marks from headline and description
            headline = headline.strip('"')
            description = description.strip('"')
            lstkeywords = [x.strip('"') for x in keywords]
            print(headline)
            print(description)
            print(lstkeywords)
            
            with ExifToolHelper() as et:
                metadata = {
                    "IPTC:Headline": headline,
                    "XMP-dc:Title": headline,
                    "IPTC:Caption-Abstract": description,
                    "EXIF:UserComment": description,
                    "XMP-dc:Description": description,
                    "IPTC:Keywords": lstkeywords,
                    "XMP-dc:Subject": lstkeywords,
                }
                et.set_tags(image_path, metadata, params=["-overwrite_original"])
            print(f"Processed image: {image_path}")

    except Exception as e:
        print(f"Error processing image {image_path}: {e}")

def main():
    """Main function to process images."""
    parser = argparse.ArgumentParser(description="Process images with Ollama and ExifTool.")
    parser.add_argument("path", help="Path to an image file or a directory containing images.")
    args = parser.parse_args()

    config = load_config()

    MODEL = {config['model']}
    TEMP = {config['temperature']}
    TONE = {config['tone']}

    if os.path.isfile(args.path):
        if args.path.lower().endswith(('.jpg', '.jpeg')):
            process_image(args.path, config)
        else:
            print("Provided file is not a JPEG image.")

    elif os.path.isdir(args.path):
        for filename in os.listdir(args.path):
            if filename.lower().endswith(('.jpg', '.jpeg')):
                image_path = os.path.join(args.path, filename)
                process_image(image_path, config)
    else:
        print("Invalid path provided.")

if __name__ == "__main__":
    main()