# Cognito User Management Tools

Terminal User Interface (TUI) and command-line tools for managing users in AWS Cognito User Pools.

## Features

- **Interactive TUI**: Full terminal-based graphical interface for user management
- **Full CRUD Operations**:
  - **Create**: Create single users with custom email/password/phone or bulk create test users
  - **Read**: List all users with status, view detailed user information and attributes
  - **Update**: Change password, update email/phone, toggle verification status, enable/disable accounts, reset MFA
  - **Delete**: Delete selected users or all users with exclusion support
- **Settings view**: View current configuration

## Installation

```bash
pip install -e .
```

## Configuration

Set the following environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_REGION=ap-southeast-1
export AWS_COGNITO_USER_POOL_ID=your_user_pool_id
export EXCLUDE_USERS=admin@example.com,protected@example.com
```

Or copy `.env.example` to `.env` and fill in your values.

## Usage

### Terminal User Interface (Recommended)

Launch the interactive TUI:

```bash
cognito-user
```

#### Main Menu

- **Create Users**: Create single users or bulk test users
- **Manage Users**: Full user management (list, view, edit, delete)
- **Settings**: View current configuration

#### Create Users Screen

- Create a single user with custom email, password, and phone number
- Bulk create test users (testuser1@example.com, testuser2@example.com, etc.)

#### Manage Users Screen

- **List**: View all users in a table with username, email, status, enabled state, and creation date
- **View**: See detailed user information including all attributes (press `v` or click View)
- **Edit**: Modify user details (press `e` or click Edit):
  - Change password
  - Update email and phone number
  - Toggle email/phone verification status
  - Enable or disable user account
  - Reset MFA settings
- **Delete**: Remove selected users or all non-excluded users

#### TUI Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `Escape` | Go back to previous screen |
| `r` | Refresh user list (on Manage Users screen) |
| `v` | View selected user details |
| `e` | Edit selected user |
| `d` | Delete selected users |
| `Tab` | Navigate between elements |
| `Enter` | Activate button / Select row for deletion |

### Command Line Interface

The original CLI commands are still available:

#### Create a Single User with Custom Email and Password

```bash
cognito-create-users --email john@example.com --password MySecurePass123!
```

Or with short flags:

```bash
cognito-create-users -e john@example.com -p MySecurePass123!
```

#### Create Multiple Test Users

Create a specified number of test users (testuser1@example.com, testuser2@example.com, etc.):

```bash
cognito-create-users 10
```

With a custom password:

```bash
cognito-create-users 10 --password CustomPass123!
```

#### Delete Users

Delete all users from the pool:

```bash
cognito-delete-users
```

Exclude specific users from deletion:

```bash
cognito-delete-users --exclude admin@example.com user@example.com
```

## Excluded Users

Users can be excluded from deletion in two ways:

1. **Environment variable**: Set `EXCLUDE_USERS` with comma-separated usernames/emails
2. **Command line**: Use `--exclude` flag with the CLI

In the TUI, excluded users are marked with `[E]` and cannot be selected for deletion.

## Project Structure

```
cognito-user/
├── src/
│   └── cognito_user/
│       ├── __init__.py
│       ├── client.py         # Cognito client factory
│       ├── config.py         # Environment configuration
│       ├── create_users.py   # User creation logic (CLI)
│       ├── delete_users.py   # User deletion logic (CLI)
│       └── tui.py            # Terminal User Interface
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## Development

Install with dev dependencies:

```bash
pip install -e ".[dev]"
```

## License

MIT
