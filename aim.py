import os
import argparse
import json
from exiftool import ExifToolHelper
import ollama
import logging
from datetime import datetime

import base64
from io import BytesIO

from IPython.display import HTML, display
from PIL import Image

from langchain_ollama import OllamaLLM

# Configuration
DEFAULT_KEYWORD_COUNT = 5
MODEL = "llava"
TONE = "concise,professional" 
TEMP = 0.5
CONFIG_FILE = "aim_config.json"
RESULTS_DIR = "." # Results file will be written in the script's execution directory

def load_config():
    """Loads configuration from a JSON file."""
    config = {"keyword_count": DEFAULT_KEYWORD_COUNT, "model": MODEL, "temperature": TEMP, "tone": TONE}
    try:
        with open(CONFIG_FILE, "r") as f:
            loaded_config = json.load(f)
            config.update(loaded_config) # Update default config with loaded values
    except FileNotFoundError:
        save_config(config)  # Create default config file if not exists
    return config

def save_config(config):
    """Saves configuration to a JSON file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def convert_to_base64(pil_image):
    """
    Convert PIL images to Base64 encoded strings

    :param pil_image: PIL image
    :return: Re-sized Base64 string
    """

    buffered = BytesIO()
    pil_image.save(buffered, format="JPEG")  # You can change the format if needed
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

def plt_img_base64(img_base64):
    """
    Display base64 encoded string as image

    :param img_base64:  Base64 string
    """
    # Create an HTML img tag with the base64 string as the source
    image_html = f'<img src="data:image/jpeg;base64,{img_base64}" />'
    # Display the image by rendering the HTML
    display(HTML(image_html))

def get_ollama_response(image_path, prompt_template, temperature=0.7, model_name=MODEL):
    """Invokes Ollama to get image information with temperature control."""
    try:
        logging.info(f"Attempting to get Ollama response for image: {image_path}")
        with open(image_path, "rb") as image_file:
            pil_image = Image.open(image_file)
            image_b64 = convert_to_base64(pil_image)
            plt_img_base64(image_b64)

        llm = OllamaLLM(model=model_name, temperature=temperature) # Set temperature directly here

        llm_response = None

        llm_with_image_context = llm.bind(images=[image_b64])
        llm_response = llm_with_image_context.invoke(prompt_template)
        
        logging.info("Successfully received response from Ollama.")
        return  llm_response.strip()
    except Exception as e:
        logging.error(f"Error processing image {image_path} with Ollama: {e}")
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

def process_image(image_path, config, results_file, report_only=False):
    """Processes a single image."""
    logging.info(f"--- Processing image: {os.path.basename(image_path)} ---")

    tone = config['tone'].split(',')
    model_name = config['model']
    temperature_setting = config['temperature']

    logging.info(f"Using tone: {tone[0]}, {tone[1]}")
    logging.info(f"Using Ollama model: {model_name}")
    logging.info(f"Using temperature setting: {temperature_setting}")

    headline = "N/A"
    description = "N/A"
    lstkeywords = []

    try:
        prompt_template = f"""
          You are a professional photojournalist. Analyze the following image and generate metadata with a {tone[0]} and {tone[1]} tone:
          Headline: Create a short, impactful title that captures the essence of the image.
          Description: Write a concise and informative summary that describes what is happening in the image.
          Keywords: List {config['keyword_count']} relevant and descriptive keywords, separated by commas.
          Format your output exactly as follows:
          Headline: ...
          Description: ...
          Keywords: ...
        """

        ollama_response = get_ollama_response(image_path, prompt_template, temperature_setting, model_name)

        if ollama_response:
            logging.info("Model raw response:\n---\n%s\n---", ollama_response)
            lines = ollama_response.split('\n')
            
            for line in lines:
                if line.startswith("Headline:"):
                    headline = line.replace("Headline:", "").strip()
                elif line.startswith("Description:"):
                    description = line.replace("Description:", "").strip()
                elif line.startswith("Keywords:"):
                    lstkeywords = extract_keywords(line)

            # Remove quotation marks from headline and description
            headline = headline.strip('"')
            description = description.strip('"')
            lstkeywords = [x.strip('"') for x in lstkeywords]

            logging.info(f"Generated Headline: \"{headline}\"")
            logging.info(f"Generated Description: \"{description}\"")
            logging.info(f"Generated Keywords: {lstkeywords}")
            
            if not report_only:
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
                logging.info(f"Successfully wrote metadata to: {os.path.basename(image_path)}")
            else:
                logging.info(f"Report-only mode: Skipped writing metadata to {os.path.basename(image_path)}")
        else:
            logging.warning(f"No Ollama response for image: {os.path.basename(image_path)}")

    except Exception as e:
        logging.error(f"An unexpected error occurred while processing image {os.path.basename(image_path)}: {e}")
    
    finally:
        # Write results to the file
        results_file.write(f"Image Name: {os.path.basename(image_path)}\n")
        results_file.write(f"  Headline: {headline}\n")
        results_file.write(f"  Description: {description}\n")
        results_file.write(f"  Keywords: {', '.join(lstkeywords)}\n")
        results_file.write("-" * 50 + "\n") # Separator for readability

def main():
    """Main function to process images."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description="Process images with Ollama and ExifTool.")
    parser.add_argument("path", help="Path to an image file or a directory containing images.")
    parser.add_argument("--report-only", action="store_true", 
                        help="If set, images' metadata will not be modified. Only a report file will be generated.")
    args = parser.parse_args()

    config = load_config()

    processed_image_count = 0
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    results_filename = f"metadata-run-{timestamp}.txt" # Will add count later

    results_file_path = os.path.join(RESULTS_DIR, results_filename)

    with open(results_file_path, "w", encoding="utf-8") as results_file:
        results_file.write(f"Metadata Processing Run - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if args.report_only:
            results_file.write("--- REPORT ONLY MODE ---\n")
        results_file.write("=" * 60 + "\n\n")

        if os.path.isfile(args.path):
            if args.path.lower().endswith(('.jpg', '.jpeg')):
                process_image(args.path, config, results_file, args.report_only)
                processed_image_count += 1
            else:
                logging.warning(f"Provided file '{args.path}' is not a JPEG image. Skipping.")

        elif os.path.isdir(args.path):
            logging.info(f"Processing all JPEG images in directory: {args.path}")
            for filename in os.listdir(args.path):
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    image_path = os.path.join(args.path, filename)
                    process_image(image_path, config, results_file, args.report_only)
                    processed_image_count += 1
                else:
                    logging.info(f"Skipping non-JPEG file: {filename}")
        else:
            logging.error(f"Invalid path provided: {args.path}. Please provide a valid file or directory path.")
        
        # Update the filename with the count of processed images
        final_results_filename = f"metadata-run-{timestamp}-{processed_image_count}_images.txt"
        os.rename(results_file_path, os.path.join(RESULTS_DIR, final_results_filename))
        logging.info(f"Processing complete. Results saved to: {os.path.join(RESULTS_DIR, final_results_filename)}")

if __name__ == "__main__":
    main()