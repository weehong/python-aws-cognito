"""Configuration management using environment variables."""

import os

from dotenv import load_dotenv

# Load .env file from current working directory
load_dotenv()


def get_aws_config():
    """Get AWS configuration from environment variables."""
    return {
        "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "region_name": os.environ.get("AWS_REGION", "ap-southeast-1"),
    }


def get_user_pool_id():
    """Get Cognito User Pool ID from environment variable."""
    return os.environ.get("AWS_COGNITO_USER_POOL_ID")


def get_excluded_users():
    """Get list of users to exclude from deletion.

    Returns:
        List of usernames to exclude, or empty list if not set.
    """
    excluded = os.environ.get("EXCLUDE_USERS", "")
    if not excluded:
        return []
    return [u.strip() for u in excluded.split(",") if u.strip()]
