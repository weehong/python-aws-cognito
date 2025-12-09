"""Create test users in AWS Cognito."""

import argparse

from botocore.exceptions import ClientError

from .client import get_cognito_client
from .config import get_user_pool_id

DEFAULT_PASSWORD = "Password123!"


def create_single_user(user_pool_id, email, password=DEFAULT_PASSWORD):
    """Create a single user in the specified Cognito User Pool.

    Args:
        user_pool_id: The Cognito User Pool ID.
        email: Email address for the user.
        password: Password to set for the user.

    Returns:
        True if successful, False otherwise.
    """
    client = get_cognito_client()

    try:
        client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "phone_number", "Value": "+6587654321"},
                {"Name": "phone_number_verified", "Value": "true"},
            ],
            MessageAction="SUPPRESS",
        )

        client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=email,
            Password=password,
            Permanent=True,
        )

        print(f"Successfully created user: {email}")
        return True

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "UsernameExistsException":
            print(f"Error: User already exists: {email}")
        else:
            print(f"Error: Failed to create {email}: {e}")
        return False


def create_test_users(user_pool_id, num_users, password=DEFAULT_PASSWORD):
    """Create test users in the specified Cognito User Pool.

    Args:
        user_pool_id: The Cognito User Pool ID.
        num_users: Number of test users to create.
        password: Password to set for all users.

    Returns:
        Tuple of (created_count, failed_count).
    """
    client = get_cognito_client()

    created_count = 0
    failed_count = 0

    for i in range(1, num_users + 1):
        email = f"testuser{i}@example.com"

        try:
            client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "phone_number", "Value": "+6587654321"},
                    {"Name": "phone_number_verified", "Value": "true"},
                ],
                MessageAction="SUPPRESS",
            )

            client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=email,
                Password=password,
                Permanent=True,
            )

            print(f"Created user: {email}")
            created_count += 1

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "UsernameExistsException":
                print(f"User already exists: {email}")
            else:
                print(f"Failed to create {email}: {e}")
            failed_count += 1

    print(f"\nSummary:")
    print(f"  Created: {created_count} users")
    print(f"  Failed/Skipped: {failed_count} users")

    return created_count, failed_count


def main():
    """CLI entry point for creating test users."""
    parser = argparse.ArgumentParser(description="Create test users in AWS Cognito")
    parser.add_argument(
        "num_users",
        type=int,
        nargs="?",
        help="Number of test users to create (optional if using --email)",
    )
    parser.add_argument(
        "--email", "-e", type=str, help="Email address for a single user"
    )
    parser.add_argument(
        "--password",
        "-p",
        type=str,
        default=DEFAULT_PASSWORD,
        help=f"Password for the user(s) (default: {DEFAULT_PASSWORD})",
    )
    args = parser.parse_args()

    user_pool_id = get_user_pool_id()
    if not user_pool_id:
        print("Error: AWS_COGNITO_USER_POOL_ID environment variable not set")
        return 1

    # Single user mode
    if args.email:
        success = create_single_user(user_pool_id, args.email, args.password)
        return 0 if success else 1

    # Bulk user mode
    if args.num_users is None:
        parser.error("num_users is required when --email is not provided")

    create_test_users(user_pool_id, args.num_users, args.password)
    return 0


if __name__ == "__main__":
    exit(main())
