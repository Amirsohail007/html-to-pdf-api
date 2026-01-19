"""
PDF generation utilities
"""
import pdfkit
import boto3
import re
import logging
from pathlib import Path
from urllib.parse import unquote
import httpx
import os
import asyncio
from playwright.async_api import async_playwright
from fastapi import HTTPException

from src.config.settings import PDF_OPTIONS, PLAYWRIGHT_PDF_OPTIONS
from src.utils.helpers import cleanup_html

# Configure logging
logger = logging.getLogger(__name__)

# Get the path to the static directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
TAILWIND_CSS_PATH = os.path.join(STATIC_DIR, "tailwind-all.css")

# Global variables for browser management
_playwright = None
_browser = None
_browser_lock = asyncio.Lock()

# Browser arguments to reduce resource usage
BROWSER_ARGS = [
    '--font-render-hinting=none', 
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-setuid-sandbox',
    '--disable-extensions',
    '--disable-accelerated-2d-canvas',
    '--disable-accelerated-jpeg-decoding',
    '--disable-accelerated-mjpeg-decode',
    '--disable-accelerated-video-decode',
    '--disable-application-cache',
    '--disable-gl-drawing-for-tests',
    '--disable-software-rasterizer'
]

async def get_browser():
    """Get or create a browser instance"""
    global _playwright, _browser
    
    async with _browser_lock:
        if _browser is None or not _browser.is_connected():
            logger.info("Creating new browser instance...")
            # Close any existing browser
            if _browser:
                try:
                    await _browser.close()
                    logger.debug("Closed existing browser")
                except Exception as e:
                    logger.warning(f"Failed to close existing browser: {e}")
                _browser = None
                
            # Close any existing playwright
            if _playwright:
                try:
                    await _playwright.__aexit__(None, None, None)
                    logger.debug("Closed existing playwright")
                except Exception as e:
                    logger.warning(f"Failed to close existing playwright: {e}")
                _playwright = None
                
            # Create new playwright and browser
            logger.debug("Launching new playwright and browser...")
            _playwright = await async_playwright().__aenter__()
            _browser = await _playwright.chromium.launch(
                headless=True,
                args=BROWSER_ARGS
            )
            logger.info("Browser instance created successfully")
        else:
            logger.debug("Reusing existing browser instance")
            
    return _browser

async def generate_pdf_with_pdfkit(request, include_css=True):
    """Generate PDF using pdfkit"""
    logger.debug(f"PDFKit generation started - include_css: {include_css}")
    options = PDF_OPTIONS.copy()
    
    try:
        if request.raw_html:
            logger.debug("Generating PDF from raw HTML")
            raw_html = unquote(request.raw_html)
            logger.debug(f"HTML content length: {len(raw_html)}")
            # If include_css is True, pass CSS file
            css_file = [TAILWIND_CSS_PATH] if include_css else []
            if css_file:
                logger.debug(f"Using CSS file: {TAILWIND_CSS_PATH}")
            pdf = pdfkit.from_string(cleanup_html(raw_html), False, options=options, css=css_file)
        elif request.url:
            logger.debug(f"Generating PDF from URL: {request.url}")
            url = request.url
            options.update({'javascript-delay': '10000'})
            pdf = pdfkit.from_url(url, False, options=options)
        else:
            logger.error("PDFKit generation failed - no raw_html or url provided")
            raise HTTPException(status_code=400, detail="Bad Request - Missing params")
        
        logger.info(f"PDFKit generation completed successfully, PDF size: {len(pdf)} bytes")
        return pdf
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDFKit generation failed with error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


async def generate_pdf_with_playwright(html_content):
    """Generate PDF using Playwright"""
    logger.debug(f"Playwright PDF generation started, HTML content length: {len(html_content)}")
    
    try:
        browser = await get_browser()
        logger.debug("Creating new page in browser")
        page = await browser.new_page()
        
        try:            
            # Set content and ensure all resources load
            logger.debug("Setting page content...")
            await page.set_content(html_content)
            
            # Wait for everything to load properly, but don't fail if timeout
            logger.debug("Waiting for network idle...")
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
                logger.debug("Network idle state reached")
            except Exception as e:
                logger.warning(f"Network idle timeout, continuing anyway: {str(e)}")
                
            await page.wait_for_timeout(300)
            
            # Generate PDF
            logger.debug("Generating PDF...")
            pdf_bytes = await page.pdf(
                format="Letter",
                print_background=True,
                margin={'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'}
            )
            
            logger.info(f"Playwright PDF generation completed successfully, PDF size: {len(pdf_bytes)} bytes")
            return pdf_bytes
        finally:
            # Close the page but keep browser alive
            logger.debug("Closing page")
            await page.close()
    except Exception as e:
        logger.error(f"Playwright PDF generation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


async def generate_pdf_with_playwright_with_header_footer(html_content, pdf_format="Letter", header_template=None, footer_template=None, margin=None, scale=0.9):
    """Generate PDF using Playwright with optional header, footer, and custom margins."""
    try:
        browser = await get_browser()
        page = await browser.new_page()
        
        try:
            await page.set_content(html_content)
            
            # Wait for everything to load properly, but don't fail if timeout
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                print(f"Network idle timeout, continuing anyway: {str(e)}")
                
            await page.wait_for_timeout(300)

            default_margin = {'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'}
            if margin:
                default_margin.update(margin)

            await page.emulate_media(media="screen")
            pdf_bytes = await page.pdf(
                format=pdf_format,
                print_background=True,
                display_header_footer=True,
                header_template=header_template or "",
                footer_template=footer_template or "",
                margin=default_margin,
                scale=scale
            )
            
            return pdf_bytes
        finally:
            # Close the page but keep browser alive
            await page.close()
    except Exception as e:
        # Log the error and raise an HTTP exception
        print(f"PDF generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

async def fetch_and_prepare_html(request, include_css=True):
    """Fetch HTML from URL or extract from request and prepare it for PDF generation"""
    logger.debug(f"Fetching and preparing HTML - include_css: {include_css}")
    html_string = ""
    
    try:
        if request.raw_html:
            logger.debug("Processing raw HTML from request")
            raw_html = unquote(request.raw_html)
            logger.debug(f"Raw HTML length: {len(raw_html)}")
            html_string = cleanup_html(raw_html)
            logger.debug(f"Cleaned HTML length: {len(html_string)}")
        elif request.url:
            logger.info(f"Fetching HTML from URL: {request.url}")
            include_css = False  # Don't inject CSS when fetching from URL
            url = request.url
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                logger.debug(f"HTTP response status: {response.status_code}")
                if response.status_code == 200:
                    logger.debug(f"Successfully fetched content, length: {len(response.text)}")
                    html_string = cleanup_html(response.text)
                else:
                    logger.error(f"Failed to fetch URL content, status code: {response.status_code}")
                    raise HTTPException(status_code=400, detail="Failed to fetch the URL content.")
        else:
            logger.error("No raw_html or url provided in request")
            raise HTTPException(status_code=400, detail="Bad Request - Missing HTML content or URL")
        
        # Inject CSS into the HTML if needed
        if include_css:
            logger.debug("Injecting CSS into HTML")
            try:
                css_string = Path(TAILWIND_CSS_PATH).read_text()
                logger.debug(f"CSS file length: {len(css_string)}")
                html_string = re.sub(
                    r'(<head.*?>)',
                    r'\1\n<style>{}</style>'.format(css_string),
                    html_string,
                    count=1,
                    flags=re.DOTALL | re.IGNORECASE
                )
                logger.debug("CSS injection completed")
            except Exception as e:
                logger.error(f"Failed to inject CSS: {str(e)}")
                # Continue without CSS rather than failing
        
        logger.info(f"HTML preparation completed, final length: {len(html_string)}")
        return html_string
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HTML preparation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"HTML preparation failed: {str(e)}")


async def save_pdf_to_s3(pdf_bytes, bucket, file_key, region):
    """Save PDF to S3 and return URL"""
    s3 = boto3.client('s3', region_name=region)
    s3.put_object(
        Bucket=bucket,
        Key=file_key,
        Body=pdf_bytes,
        ContentType='application/pdf'
    )
    
    from src.utils.helpers import generate_presigned_url
    return generate_presigned_url(bucket, file_key, region)

async def generate_minimal_test_pdf():
    """Generate a minimal PDF to test if the system is functioning properly"""
    minimal_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Health Check</title></head>
    <body><p>Health check test.</p></body>
    </html>
    """
    try:
        # Use our reusable browser
        browser = await get_browser()
        page = await browser.new_page()
        
        try:
            await page.set_content(minimal_html)
            pdf_bytes = await page.pdf(format="A4")
            return httpx.Response(200, content=pdf_bytes)
        finally:
            await page.close()
    except Exception as e:
        print(f"Health check PDF generation error: {str(e)}")
        return httpx.Response(500)
