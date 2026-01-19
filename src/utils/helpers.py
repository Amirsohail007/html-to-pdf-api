"""
Utility functions for the PDF API
"""
import boto3
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup
from src.config.settings import PDF_EXPIRY_TIME

def generate_presigned_url(bucket, file_key, region):
    """Generate a presigned URL for accessing a S3 object"""
    s3_client = boto3.client('s3', region_name=region)
    try:
        response = s3_client.generate_presigned_url(
            'get_object', 
            Params={'Bucket': bucket, 'Key': file_key},
            ExpiresIn=PDF_EXPIRY_TIME
        )
    except ClientError:
        return None
    return response


def cleanup_html(html_content):
    """Clean up HTML content to prevent issues during PDF generation"""
    # Parse the HTML using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Do cleanup operations, such as removing invalid elements or attributes
    # For example, to remove the 'undefined' src attribute from img tags
    for img_tag in soup.find_all('img'):
        if img_tag.get('src') == 'undefined' or img_tag.get('src') == 'null':
            img_tag['src'] = ''  # Set src attribute to empty string

    # Ensure HTML has proper head and body tags
    if not soup.head:
        soup = BeautifulSoup(f"<html><head><meta charset='utf-8'></head><body>{soup}</body></html>", 'html.parser')

    # Return the cleaned HTML as a string
    return str(soup)
