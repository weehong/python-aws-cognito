"""Delete users from AWS Cognito."""

import argparse

from botocore.exceptions import ClientError

from .client import get_cognito_client
from .config import get_excluded_users, get_user_pool_id


def delete_all_users(user_pool_id, excluded_usernames=None):
    """Delete all users from the specified Cognito User Pool.

    Args:
        user_pool_id: The Cognito User Pool ID.
        excluded_usernames: List of usernames to exclude from deletion.

    Returns:
        Tuple of (deleted_count, skipped_count).
    """
    if excluded_usernames is None:
        excluded_usernames = []

    excluded_set = set(excluded_usernames)
    client = get_cognito_client()

    pagination_token = None
    deleted_count = 0
    skipped_count = 0

    try:
        while True:
            kwargs = {"UserPoolId": user_pool_id}
            if pagination_token:
                kwargs["PaginationToken"] = pagination_token

            response = client.list_users(**kwargs)

            for user in response["Users"]:
                username = user["Username"]

                if username in excluded_set:
                    print(f"Skipping excluded user: {username}")
                    skipped_count += 1
                    continue

                print(f"Deleting user: {username}")
                client.admin_delete_user(
                    UserPoolId=user_pool_id,
                    Username=username,
                )
                deleted_count += 1

            pagination_token = response.get("PaginationToken")
            if not pagination_token:
                break

        print(f"\nSummary:")
        print(f"  Deleted: {deleted_count} users")
        print(f"  Skipped: {skipped_count} users (excluded)")

    except ClientError as e:
        print(f"An error occurred: {e}")

    return deleted_count, skipped_count


def main():
    """CLI entry point for deleting users."""
    parser = argparse.ArgumentParser(description="Delete users from AWS Cognito")
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Usernames to exclude from deletion",
    )
    args = parser.parse_args()

    user_pool_id = get_user_pool_id()
    if not user_pool_id:
        print("Error: AWS_COGNITO_USER_POOL_ID environment variable not set")
        return 1

    # Combine excluded users from environment variable and command line
    excluded_users = get_excluded_users() + args.exclude
    delete_all_users(user_pool_id, excluded_users)
    return 0


if __name__ == "__main__":
    exit(main())
