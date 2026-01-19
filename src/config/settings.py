"""
Configuration settings for the PDF API
"""

DEFAULT_BUCKET = "dev-pdf-generator-api-assets"
DEFAULT_REGION = "us-west-2"
PDF_EXPIRY_TIME = 3600  # URL expiry time in seconds

# PDF generation options
PDF_OPTIONS = {
    'page-size': 'A4',
    'margin-top': '1cm',
    'margin-right': '1cm',
    'margin-bottom': '1cm',
    'margin-left': '1cm',
    'enable-local-file-access': True
}

# Playwright PDF options
PLAYWRIGHT_PDF_OPTIONS = {
    'format': 'Letter',
    'margin': {'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'},
    'print_background': True
}
