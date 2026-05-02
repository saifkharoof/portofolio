import boto3
import io
from botocore.exceptions import ClientError
from app.core.config import settings
from loguru import logger
from langchain_community.document_loaders import PyPDFLoader

class StorageService:
    def __init__(self):
        self.bucket = settings.r2_bucket_name

        if settings.r2_endpoint_url and settings.r2_access_key_id:
            self.s3 = boto3.client(
                "s3",
                endpoint_url=settings.r2_endpoint_url,
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                region_name="auto",
            )
        else:
            self.s3 = None

    def get_cv_text(self) -> str:
        """
        Download CV.pdf from R2 bucket and extract its text.
        """
        if not self.s3:
            logger.warning("No S3 client configured. Cannot fetch CV.pdf from R2.")
            return "CV data is currently unavailable."
            
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key="Saif_Resume.pdf")
            pdf_bytes = response['Body'].read()
            
            # Save to temporary file to use with PyPDFLoader
            # PyPDFLoader currently expects a file path
            temp_path = "/tmp/Saif_Resume.pdf"
            with open(temp_path, "wb") as f:
                f.write(pdf_bytes)
                
            loader = PyPDFLoader(temp_path)
            pages = loader.load()
            
            text = "\n".join([page.page_content for page in pages])
            return text
            
        except ClientError as e:
            logger.error(f"Error downloading CV.pdf from R2: {e}")
            return "CV data is currently unavailable."
        except Exception as e:
            logger.error(f"Error parsing CV.pdf: {e}")
            return "CV data is currently unavailable."

storage = StorageService()
