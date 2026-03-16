import logging

from fastapi import UploadFile
from fastapi.responses import StreamingResponse
import aioboto3

logger = logging.getLogger()
aws = aioboto3.Session()

BUCKET_NAME = "musikii-dev"

async def getS3Client():
    async with aws.client("s3") as s3: #type: ignore
        yield s3

async def newFile(s3, file: UploadFile, file_key: str) -> int:
    try:
        await s3.upload_fileobj(
            file.file,
            Bucket=BUCKET_NAME,
            Key=file_key
        )
        return 0
    except Exception as e:
        logger.error("Error while uploading file to S3 : ", e)
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