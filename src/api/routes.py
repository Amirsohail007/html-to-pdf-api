"""
API routes for PDF generation
"""
import uuid
import time
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Response

from src.models.schemas import PDFRequest, PDFResponse
from src.utils.pdf_generator import (
    generate_pdf_with_pdfkit, 
    generate_pdf_with_playwright, 
    fetch_and_prepare_html,
    save_pdf_to_s3,
    generate_pdf_with_playwright_with_header_footer
)
from src.config.settings import DEFAULT_BUCKET, DEFAULT_REGION

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["pdf"])
router_v2 = APIRouter(prefix="/v2", tags=["pdf"])

@router.post("/pdf", response_model=PDFResponse)
async def convert_html_to_pdf(request: PDFRequest, include_css: bool = True, save_pdf_s3: bool = True):
    """
    Convert HTML to PDF using PDFKit
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    
    logger.info(f"[{request_id}] Starting PDF generation (PDFKit) - include_css: {include_css}, save_to_s3: {save_pdf_s3}")
    logger.debug(f"[{request_id}] Request details: has_raw_html={bool(request.raw_html)}, has_url={bool(request.url)}")
    
    try:
        # Use request model values
        bucket = request.bucket if request.bucket else DEFAULT_BUCKET
        file_key = request.file_key if request.file_key else f"{datetime.now().strftime('%Y-%m-%d')}/{uuid.uuid4()}.pdf"
        region = request.region if request.region else DEFAULT_REGION
        
        logger.info(f"[{request_id}] PDF destination: bucket={bucket}, file_key={file_key}, region={region}")

        # Generate PDF
        logger.info(f"[{request_id}] Generating PDF with PDFKit...")
        pdf_start = time.time()
        pdf = await generate_pdf_with_pdfkit(request, include_css)
        pdf_duration = time.time() - pdf_start
        logger.info(f"[{request_id}] PDF generation completed in {pdf_duration:.2f}s, size: {len(pdf)} bytes")

        if save_pdf_s3:
            # Upload PDF to S3 and get URL
            logger.info(f"[{request_id}] Uploading PDF to S3...")
            s3_start = time.time()
            presigned_url = await save_pdf_to_s3(pdf, bucket, file_key, region)
            s3_duration = time.time() - s3_start
            
            if presigned_url:
                total_duration = time.time() - start_time
                logger.info(f"[{request_id}] PDF upload completed in {s3_duration:.2f}s, total request time: {total_duration:.2f}s")
                logger.info(f"[{request_id}] Success - returning presigned URL")
                return {"url": presigned_url}
            else:
                logger.error(f"[{request_id}] Failed to upload PDF to S3")
                raise HTTPException(status_code=500, detail="Failed to generate pdf")
        else:
            total_duration = time.time() - start_time
            logger.info(f"[{request_id}] Returning PDF directly, total request time: {total_duration:.2f}s")
            # Return the PDF file directly
            return Response(
                content=pdf,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=document.pdf"}
            )
    except HTTPException:
        logger.error(f"[{request_id}] HTTP exception occurred")
        raise
    except Exception as e:
        total_duration = time.time() - start_time
        logger.error(f"[{request_id}] Unexpected error after {total_duration:.2f}s: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router_v2.post("/pdf", response_model=PDFResponse)
async def convert_html_to_pdf_v2(request: PDFRequest, include_css: bool = True, save_pdf_s3: bool = True):
    """
    Convert HTML to PDF using Playwright
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    
    logger.info(f"[{request_id}] Starting PDF generation (Playwright V2) - include_css: {include_css}, save_to_s3: {save_pdf_s3}")
    logger.debug(f"[{request_id}] Request details: has_raw_html={bool(request.raw_html)}, has_url={bool(request.url)}")
    
    try:
        # Use request model values
        bucket = request.bucket if request.bucket else DEFAULT_BUCKET
        file_key = request.file_key if request.file_key else f"{datetime.now().strftime('%Y-%m-%d')}/{uuid.uuid4()}.pdf"
        region = request.region if request.region else DEFAULT_REGION
        
        logger.info(f"[{request_id}] PDF destination: bucket={bucket}, file_key={file_key}, region={region}")

        if not request.raw_html and not request.url:
            logger.error(f"[{request_id}] Bad request - missing both raw_html and url parameters")
            raise HTTPException(status_code=400, detail="Bad Request - Missing params")

        # Fetch and prepare HTML
        logger.info(f"[{request_id}] Fetching and preparing HTML content...")
        html_start = time.time()
        html_string = await fetch_and_prepare_html(request, include_css)
        html_duration = time.time() - html_start
        logger.info(f"[{request_id}] HTML preparation completed in {html_duration:.2f}s, content length: {len(html_string)}")

        # Generate PDF
        logger.info(f"[{request_id}] Generating PDF with Playwright...")
        pdf_start = time.time()
        pdf_bytes = await generate_pdf_with_playwright(html_content=html_string)
        pdf_duration = time.time() - pdf_start
        logger.info(f"[{request_id}] PDF generation completed in {pdf_duration:.2f}s, size: {len(pdf_bytes)} bytes")

        if save_pdf_s3:
            # Upload PDF to S3 and get URL
            logger.info(f"[{request_id}] Uploading PDF to S3...")
            s3_start = time.time()
            presigned_url = await save_pdf_to_s3(pdf_bytes, bucket, file_key, region)
            s3_duration = time.time() - s3_start

            if presigned_url:
                total_duration = time.time() - start_time
                logger.info(f"[{request_id}] PDF upload completed in {s3_duration:.2f}s, total request time: {total_duration:.2f}s")
                logger.info(f"[{request_id}] Success - returning presigned URL")
                return {"url": presigned_url}
            else:
                logger.error(f"[{request_id}] Failed to upload PDF to S3")
                raise HTTPException(status_code=500, detail="Failed to generate PDF")
        else:
            total_duration = time.time() - start_time
            logger.info(f"[{request_id}] Returning PDF directly, total request time: {total_duration:.2f}s")
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=document.pdf"}
            )
    except HTTPException:
        logger.error(f"[{request_id}] HTTP exception occurred")
        raise
    except Exception as e:
        total_duration = time.time() - start_time
        logger.error(f"[{request_id}] Unexpected error after {total_duration:.2f}s: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 

@router.post("/pdf-with-header-footer", response_model=PDFResponse)
async def convert_html_to_pdf_with_header_footer(request: PDFRequest, include_css: bool = True, save_pdf_s3: bool = True):
    """
    Convert HTML to PDF using Playwright with header/footer support
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    
    logger.info(f"[{request_id}] Starting PDF generation with header/footer (Playwright) - include_css: {include_css}, save_to_s3: {save_pdf_s3}")
    logger.debug(f"[{request_id}] Request details: has_raw_html={bool(request.raw_html)}, has_url={bool(request.url)}")
    logger.debug(f"[{request_id}] PDF options: format={request.pdf_format}, scale={request.scale}, has_header={bool(request.header_template)}, has_footer={bool(request.footer_template)}")
    
    try:
        # Use request model values
        bucket = request.bucket if request.bucket else DEFAULT_BUCKET
        file_key = request.file_key if request.file_key else f"{datetime.now().strftime('%Y-%m-%d')}/{uuid.uuid4()}.pdf"
        region = request.region if request.region else DEFAULT_REGION
        
        logger.info(f"[{request_id}] PDF destination: bucket={bucket}, file_key={file_key}, region={region}")

        if not request.raw_html and not request.url:
            logger.error(f"[{request_id}] Bad request - missing both raw_html and url parameters")
            raise HTTPException(status_code=400, detail="Bad Request - Missing params")

        # Fetch and prepare HTML
        logger.info(f"[{request_id}] Fetching and preparing HTML content...")
        html_start = time.time()
        html_string = await fetch_and_prepare_html(request, include_css)
        html_duration = time.time() - html_start
        logger.info(f"[{request_id}] HTML preparation completed in {html_duration:.2f}s, content length: {len(html_string)}")
            
        # Generate PDF
        logger.info(f"[{request_id}] Generating PDF with Playwright (with header/footer)...")
        pdf_start = time.time()
        pdf_bytes = await generate_pdf_with_playwright_with_header_footer(
            html_content=html_string, 
            pdf_format=request.pdf_format, 
            scale=request.scale, 
            margin=request.margin, 
            header_template=request.header_template, 
            footer_template=request.footer_template
        )
        pdf_duration = time.time() - pdf_start
        logger.info(f"[{request_id}] PDF generation completed in {pdf_duration:.2f}s, size: {len(pdf_bytes)} bytes")

        if save_pdf_s3:
            # Upload PDF to S3 and get URL
            logger.info(f"[{request_id}] Uploading PDF to S3...")
            s3_start = time.time()
            presigned_url = await save_pdf_to_s3(pdf_bytes, bucket, file_key, region)
            s3_duration = time.time() - s3_start

            if presigned_url:
                total_duration = time.time() - start_time
                logger.info(f"[{request_id}] PDF upload completed in {s3_duration:.2f}s, total request time: {total_duration:.2f}s")
                logger.info(f"[{request_id}] Success - returning presigned URL")
                return {"url": presigned_url}
            else:
                logger.error(f"[{request_id}] Failed to upload PDF to S3")
                raise HTTPException(status_code=500, detail="Failed to generate PDF")
        else:
            total_duration = time.time() - start_time
            logger.info(f"[{request_id}] Returning PDF directly, total request time: {total_duration:.2f}s")
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=document.pdf"}
            )
    except HTTPException:
        logger.error(f"[{request_id}] HTTP exception occurred")
        raise
    except Exception as e:
        total_duration = time.time() - start_time
        logger.error(f"[{request_id}] Unexpected error after {total_duration:.2f}s: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 