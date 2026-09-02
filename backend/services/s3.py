import logging
import io

from fastapi import UploadFile, HTTPException
import aioboto3

logger = logging.getLogger()
aws = aioboto3.Session()

BUCKET_NAME = "musikii-dev"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB limit
ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/ogg",
    "audio/flac",
    "audio/aac",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mp4",
    "audio/webm",
    "application/octet-stream"  # Some clients may send this for audio files
}

async def getS3Client():
    async with aws.client("s3") as s3: #type: ignore
        yield s3

async def newFile(s3, file: UploadFile, file_key: str) -> int:
    try:
        # Validate content type
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            logger.warning(f"Rejected upload with invalid content type: {file.content_type}")
            return 3  # New error code for invalid content type
        
        # Read file with size limit to prevent unbounded uploads
        file_content = io.BytesIO()
        total_size = 0
        chunk_size = 1024 * 1024  # 1 MB chunks
        
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                logger.warning(f"Rejected upload exceeding size limit: {total_size} bytes")
                return 4  # New error code for file too large
            
            file_content.write(chunk)
        
        # Reset to beginning for upload
        file_content.seek(0)
        
        # Upload to S3
        await s3.upload_fileobj(
            file_content,
            Bucket=BUCKET_NAME,
            Key=file_key
        )
        return 0
    except Exception as e:
        logger.error(f"Error while uploading file to S3: {e}")
        return 1
    
async def removeFile(s3, file_key: str) -> int:
    try:
        await s3.delete_object(
            Bucket=BUCKET_NAME,
            Key=file_key
        )
        return 0
    except Exception as e:
        logger.error("Error while removing file from S3 : ", e)
        return 1