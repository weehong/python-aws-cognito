"""Cognito client factory."""

import boto3

from .config import get_aws_config


def get_cognito_client():
    """Create and return a Cognito IDP client."""
    config = get_aws_config()
    return boto3.client("cognito-idp", **config)
