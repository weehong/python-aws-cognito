"""Terminal User Interface for AWS Cognito User Management."""

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    SelectionList,
    Static,
)

from botocore.exceptions import ClientError

from .client import get_cognito_client
from .config import get_excluded_users, get_user_pool_id

DEFAULT_PASSWORD = "Password123!"


def fetch_user_pool_groups(user_pool_id: str) -> list[tuple[str, str]]:
    """Fetch all groups from the Cognito User Pool.

    Args:
        user_pool_id: The Cognito User Pool ID.

    Returns:
        List of tuples (group_name, group_name) for use in Select/SelectionList widgets.
    """
    if not user_pool_id:
        return []

    try:
        client = get_cognito_client()
        groups = []
        next_token = None

        while True:
            kwargs = {"UserPoolId": user_pool_id}
            if next_token:
                kwargs["NextToken"] = next_token

            response = client.list_groups(**kwargs)

            for group in response.get("Groups", []):
                group_name = group["GroupName"]
                groups.append((group_name, group_name))

            next_token = response.get("NextToken")
            if not next_token:
                break

        return sorted(groups, key=lambda x: x[0])
    except ClientError:
        return []


def get_user_groups(user_pool_id: str, username: str) -> list[str]:
    """Get the groups a user belongs to.

    Args:
        user_pool_id: The Cognito User Pool ID.
        username: The username to look up.

    Returns:
        List of group names the user belongs to.
    """
    if not user_pool_id or not username:
        return []

    try:
        client = get_cognito_client()
        groups = []
        next_token = None

        while True:
            kwargs = {"UserPoolId": user_pool_id, "Username": username}
            if next_token:
                kwargs["NextToken"] = next_token

            response = client.admin_list_groups_for_user(**kwargs)

            for group in response.get("Groups", []):
                groups.append(group["GroupName"])

            next_token = response.get("NextToken")
            if not next_token:
                break

        return groups
    except ClientError:
        return []


def add_user_to_group(user_pool_id: str, username: str, group_name: str) -> tuple[bool, str]:
    """Add a user to a group.

    Args:
        user_pool_id: The Cognito User Pool ID.
        username: The username to add.
        group_name: The group to add the user to.

    Returns:
        Tuple of (success, error_message). error_message is empty on success.
    """
    try:
        client = get_cognito_client()
        client.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=username,
            GroupName=group_name,
        )
        return True, ""
    except ClientError as e:
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        return False, error_msg


def remove_user_from_group(user_pool_id: str, username: str, group_name: str) -> tuple[bool, str]:
    """Remove a user from a group.

    Args:
        user_pool_id: The Cognito User Pool ID.
        username: The username to remove.
        group_name: The group to remove the user from.

    Returns:
        Tuple of (success, error_message). error_message is empty on success.
    """
    try:
        client = get_cognito_client()
        client.admin_remove_user_from_group(
            UserPoolId=user_pool_id,
            Username=username,
            GroupName=group_name,
        )
        return True, ""
    except ClientError as e:
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        return False, error_msg


class StatusBar(Static):
    """Status bar widget for displaying messages."""

    def set_message(self, message: str, error: bool = False) -> None:
        """Set the status message."""
        self.update(message)
        self.set_class(error, "error")


class ViewUserScreen(Screen):
    """Screen for viewing user details."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, username: str) -> None:
        super().__init__()
        self.username = username

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            VerticalScroll(
                Label("User Details", classes="title"),
                Static(id="user-details"),
                Label("", classes="separator"),
                Label("Group Membership", classes="subtitle"),
                Static(id="user-groups"),
                Label("", classes="separator"),
                Label("User Attributes", classes="subtitle"),
                Static(id="user-attributes"),
                Horizontal(
                    Button("Edit User", id="edit", variant="primary"),
                    Button("Back", id="back"),
                    classes="button-row",
                ),
                StatusBar(id="status"),
                classes="details-container",
            ),
            id="view-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Load and display user details."""
        self.load_user_details()

    def load_user_details(self) -> None:
        """Fetch and display user details from Cognito."""
        status = self.query_one("#status", StatusBar)
        user_pool_id = get_user_pool_id()

        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        try:
            client = get_cognito_client()
            response = client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=self.username,
            )

            # Basic user info
            user_status = response.get("UserStatus", "UNKNOWN")
            enabled = response.get("Enabled", False)
            created = response.get("UserCreateDate", "")
            modified = response.get("UserLastModifiedDate", "")

            if created:
                created = created.strftime("%Y-%m-%d %H:%M:%S")
            if modified:
                modified = modified.strftime("%Y-%m-%d %H:%M:%S")

            details_text = f"""Username: {self.username}
Status: {user_status}
Enabled: {'Yes' if enabled else 'No'}
Created: {created}
Last Modified: {modified}
"""
            self.query_one("#user-details", Static).update(details_text)

            # User groups
            user_groups = get_user_groups(user_pool_id, self.username)
            if user_groups:
                groups_text = "  " + ", ".join(user_groups)
            else:
                groups_text = "  (none)"
            self.query_one("#user-groups", Static).update(groups_text)

            # User attributes
            attributes = response.get("UserAttributes", [])
            attr_lines = []
            for attr in attributes:
                name = attr["Name"]
                value = attr["Value"]
                # Mask sensitive values
                if name == "sub":
                    value = value[:8] + "..." + value[-4:]
                attr_lines.append(f"  {name}: {value}")

            attr_text = "\n".join(attr_lines) if attr_lines else "  No attributes"
            self.query_one("#user-attributes", Static).update(attr_text)

            status.set_message(f"Loaded user: {self.username}")

        except ClientError as e:
            status.set_message(f"Error loading user: {e}", error=True)

    @on(Button.Pressed, "#edit")
    def edit_user(self) -> None:
        """Open the edit user screen."""
        self.app.push_screen(EditUserScreen(self.username))

    @on(Button.Pressed, "#back")
    def go_back(self) -> None:
        """Return to previous screen."""
        self.app.pop_screen()


class EditUserScreen(Screen):
    """Screen for editing user details."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, username: str) -> None:
        super().__init__()
        self.username = username
        self.user_enabled = True
        self.current_groups: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            VerticalScroll(
                Label(f"Edit User: {self.username}", classes="title"),
                Label("Change Password", classes="subtitle"),
                Horizontal(
                    Label("New Password:", classes="label"),
                    Input(placeholder="Enter new password", id="new-password", password=True),
                    classes="form-row",
                ),
                Horizontal(
                    Button("Update Password", id="update-password", variant="primary"),
                    classes="button-row",
                ),
                Label("", classes="separator"),
                Label("Update Attributes", classes="subtitle"),
                Horizontal(
                    Label("Email:", classes="label"),
                    Input(placeholder="user@example.com", id="email"),
                    classes="form-row",
                ),
                Horizontal(
                    Label("Phone:", classes="label"),
                    Input(placeholder="+6512345678", id="phone"),
                    classes="form-row",
                ),
                Horizontal(
                    Checkbox("Email Verified", id="email-verified"),
                    Checkbox("Phone Verified", id="phone-verified"),
                    classes="checkbox-row",
                ),
                Horizontal(
                    Button("Update Attributes", id="update-attrs", variant="primary"),
                    classes="button-row",
                ),
                Label("", classes="separator"),
                Label("Group Membership", classes="subtitle"),
                Horizontal(
                    Label("Current Groups:", classes="label"),
                    Static("Loading...", id="current-groups"),
                    classes="form-row",
                ),
                Horizontal(
                    Label("Add to Group:", classes="label"),
                    Select([], id="add-group", prompt="Select a group"),
                    classes="form-row",
                ),
                Horizontal(
                    Button("Add to Group", id="add-to-group", variant="primary"),
                    Button("Remove from Group", id="remove-from-group", variant="warning"),
                    classes="button-row",
                ),
                Label("", classes="separator"),
                Label("Account Status", classes="subtitle"),
                Horizontal(
                    Checkbox("Account Enabled", id="account-enabled"),
                    classes="checkbox-row",
                ),
                Horizontal(
                    Button("Update Status", id="update-status", variant="primary"),
                    Button("Reset MFA", id="reset-mfa", variant="warning"),
                    classes="button-row",
                ),
                Label("", classes="separator"),
                Horizontal(
                    Button("Back", id="back"),
                    classes="button-row",
                ),
                StatusBar(id="status"),
                classes="edit-container",
            ),
            id="edit-outer",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Load current user data."""
        self.load_user_data()
        self.load_groups()

    def load_groups(self) -> None:
        """Load available groups and user's current groups."""
        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            return

        # Load all available groups for the dropdown
        all_groups = fetch_user_pool_groups(user_pool_id)
        group_select = self.query_one("#add-group", Select)
        group_select.set_options(all_groups)

        # Load user's current groups
        self.current_groups = get_user_groups(user_pool_id, self.username)
        current_groups_display = self.query_one("#current-groups", Static)
        if self.current_groups:
            current_groups_display.update(", ".join(self.current_groups))
        else:
            current_groups_display.update("(none)")

    def load_user_data(self) -> None:
        """Load current user attributes."""
        status = self.query_one("#status", StatusBar)
        user_pool_id = get_user_pool_id()

        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        try:
            client = get_cognito_client()
            response = client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=self.username,
            )

            # Set enabled status
            self.user_enabled = response.get("Enabled", True)
            self.query_one("#account-enabled", Checkbox).value = self.user_enabled

            # Set attributes
            for attr in response.get("UserAttributes", []):
                name = attr["Name"]
                value = attr["Value"]

                if name == "email":
                    self.query_one("#email", Input).value = value
                elif name == "phone_number":
                    self.query_one("#phone", Input).value = value
                elif name == "email_verified":
                    self.query_one("#email-verified", Checkbox).value = value.lower() == "true"
                elif name == "phone_number_verified":
                    self.query_one("#phone-verified", Checkbox).value = value.lower() == "true"

            status.set_message(f"Loaded user data for: {self.username}")

        except ClientError as e:
            status.set_message(f"Error loading user: {e}", error=True)

    @on(Button.Pressed, "#update-password")
    def update_password(self) -> None:
        """Update user password."""
        status = self.query_one("#status", StatusBar)
        new_password = self.query_one("#new-password", Input).value.strip()

        if not new_password:
            status.set_message("Error: Password is required", error=True)
            return

        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        try:
            client = get_cognito_client()
            client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=self.username,
                Password=new_password,
                Permanent=True,
            )
            status.set_message("Password updated successfully")
            self.query_one("#new-password", Input).value = ""

        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            status.set_message(f"Error: {error_msg}", error=True)

    @on(Button.Pressed, "#update-attrs")
    def update_attributes(self) -> None:
        """Update user attributes."""
        status = self.query_one("#status", StatusBar)
        email = self.query_one("#email", Input).value.strip()
        phone = self.query_one("#phone", Input).value.strip()
        email_verified = self.query_one("#email-verified", Checkbox).value
        phone_verified = self.query_one("#phone-verified", Checkbox).value

        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        attributes = []
        if email:
            attributes.append({"Name": "email", "Value": email})
            attributes.append({"Name": "email_verified", "Value": str(email_verified).lower()})
        if phone:
            attributes.append({"Name": "phone_number", "Value": phone})
            attributes.append({"Name": "phone_number_verified", "Value": str(phone_verified).lower()})

        if not attributes:
            status.set_message("Error: No attributes to update", error=True)
            return

        try:
            client = get_cognito_client()
            client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=self.username,
                UserAttributes=attributes,
            )
            status.set_message("Attributes updated successfully")

        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            status.set_message(f"Error: {error_msg}", error=True)

    @on(Button.Pressed, "#update-status")
    def update_status(self) -> None:
        """Enable or disable user account."""
        status = self.query_one("#status", StatusBar)
        enabled = self.query_one("#account-enabled", Checkbox).value

        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        try:
            client = get_cognito_client()
            if enabled:
                client.admin_enable_user(
                    UserPoolId=user_pool_id,
                    Username=self.username,
                )
                status.set_message("User account enabled")
            else:
                client.admin_disable_user(
                    UserPoolId=user_pool_id,
                    Username=self.username,
                )
                status.set_message("User account disabled")

        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            status.set_message(f"Error: {error_msg}", error=True)

    @on(Button.Pressed, "#reset-mfa")
    def reset_mfa(self) -> None:
        """Reset user MFA settings."""
        status = self.query_one("#status", StatusBar)

        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        try:
            client = get_cognito_client()
            client.admin_set_user_mfa_preference(
                UserPoolId=user_pool_id,
                Username=self.username,
                SMSMfaSettings={"Enabled": False, "PreferredMfa": False},
                SoftwareTokenMfaSettings={"Enabled": False, "PreferredMfa": False},
            )
            status.set_message("MFA settings reset successfully")

        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            status.set_message(f"Error: {error_msg}", error=True)

    @on(Button.Pressed, "#add-to-group")
    def add_to_group(self) -> None:
        """Add user to selected group."""
        status = self.query_one("#status", StatusBar)
        group_select = self.query_one("#add-group", Select)
        selected_group = group_select.value if group_select.value != Select.BLANK else None

        if not selected_group:
            status.set_message("Error: Please select a group", error=True)
            return

        if selected_group in self.current_groups:
            status.set_message(f"User is already in group '{selected_group}'", error=True)
            return

        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        success, error_msg = add_user_to_group(user_pool_id, self.username, selected_group)
        if success:
            status.set_message(f"Added user to group '{selected_group}'")
            self.load_groups()  # Refresh group display
        else:
            status.set_message(f"Error: {error_msg}", error=True)

    @on(Button.Pressed, "#remove-from-group")
    def remove_from_group(self) -> None:
        """Remove user from selected group."""
        status = self.query_one("#status", StatusBar)
        group_select = self.query_one("#add-group", Select)
        selected_group = group_select.value if group_select.value != Select.BLANK else None

        if not selected_group:
            status.set_message("Error: Please select a group", error=True)
            return

        if selected_group not in self.current_groups:
            status.set_message(f"User is not in group '{selected_group}'", error=True)
            return

        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        success, error_msg = remove_user_from_group(user_pool_id, self.username, selected_group)
        if success:
            status.set_message(f"Removed user from group '{selected_group}'")
            self.load_groups()  # Refresh group display
        else:
            status.set_message(f"Error: {error_msg}", error=True)

    @on(Button.Pressed, "#back")
    def go_back(self) -> None:
        """Return to previous screen."""
        self.app.pop_screen()


class CreateUserScreen(Screen):
    """Screen for creating users."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            VerticalScroll(
                Label("Create User", classes="title"),
                Horizontal(
                    Label("Email:", classes="label"),
                    Input(placeholder="user@example.com", id="email"),
                    classes="form-row",
                ),
                Horizontal(
                    Label("Password:", classes="label"),
                    Input(placeholder=DEFAULT_PASSWORD, id="password", password=True),
                    classes="form-row",
                ),
                Horizontal(
                    Label("Phone:", classes="label"),
                    Input(placeholder="+6587654321", id="phone"),
                    classes="form-row",
                ),
                Horizontal(
                    Label("Group:", classes="label"),
                    Select([], id="group", prompt="Select a group (optional)"),
                    classes="form-row",
                ),
                Horizontal(
                    Button("Create User", id="create-single", variant="primary"),
                    Button("Back", id="back"),
                    classes="button-row",
                ),
                Label("", classes="separator"),
                Label("Bulk Create Test Users", classes="subtitle"),
                Horizontal(
                    Label("Number of users:", classes="label"),
                    Input(placeholder="10", id="num-users"),
                    classes="form-row",
                ),
                Horizontal(
                    Label("Group:", classes="label"),
                    Select([], id="bulk-group", prompt="Select a group (optional)"),
                    classes="form-row",
                ),
                Horizontal(
                    Button("Create Test Users", id="create-bulk", variant="primary"),
                    classes="button-row",
                ),
                StatusBar(id="status"),
                classes="form-container",
            ),
            id="create-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Load available groups when screen mounts."""
        self.load_groups()

    def load_groups(self) -> None:
        """Load available groups from Cognito."""
        user_pool_id = get_user_pool_id()
        groups = fetch_user_pool_groups(user_pool_id)

        group_select = self.query_one("#group", Select)
        bulk_group_select = self.query_one("#bulk-group", Select)

        group_select.set_options(groups)
        bulk_group_select.set_options(groups)

    @on(Button.Pressed, "#create-single")
    def create_single_user(self) -> None:
        """Create a single user."""
        email = self.query_one("#email", Input).value.strip()
        password = self.query_one("#password", Input).value.strip() or DEFAULT_PASSWORD
        phone = self.query_one("#phone", Input).value.strip() or "+6587654321"
        group_select = self.query_one("#group", Select)
        selected_group = group_select.value if group_select.value != Select.BLANK else None
        status = self.query_one("#status", StatusBar)

        if not email:
            status.set_message("Error: Email is required", error=True)
            return

        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        try:
            client = get_cognito_client()
            client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "phone_number", "Value": phone},
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

            # Add user to group if selected
            group_msg = ""
            if selected_group:
                success, error_msg = add_user_to_group(user_pool_id, email, selected_group)
                if success:
                    group_msg = f" and added to group '{selected_group}'"
                else:
                    group_msg = f" (group error: {error_msg})"

            status.set_message(f"Successfully created user: {email}{group_msg}")
            self.query_one("#email", Input).value = ""
            self.query_one("#password", Input).value = ""
            self.query_one("#phone", Input).value = ""
            group_select.value = Select.BLANK
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "UsernameExistsException":
                status.set_message(f"Error: User already exists: {email}", error=True)
            else:
                error_msg = e.response.get("Error", {}).get("Message", str(e))
                status.set_message(f"Error: {error_msg}", error=True)

    @on(Button.Pressed, "#create-bulk")
    def create_bulk_users(self) -> None:
        """Create multiple test users."""
        num_users_str = self.query_one("#num-users", Input).value.strip()
        bulk_group_select = self.query_one("#bulk-group", Select)
        selected_group = bulk_group_select.value if bulk_group_select.value != Select.BLANK else None
        status = self.query_one("#status", StatusBar)

        if not num_users_str:
            status.set_message("Error: Number of users is required", error=True)
            return

        try:
            num_users = int(num_users_str)
            if num_users < 1:
                raise ValueError()
        except ValueError:
            status.set_message("Error: Please enter a valid positive number", error=True)
            return

        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        client = get_cognito_client()
        created = 0
        failed = 0
        group_added = 0

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
                    Password=DEFAULT_PASSWORD,
                    Permanent=True,
                )
                created += 1

                # Add to group if selected
                if selected_group:
                    success, _ = add_user_to_group(user_pool_id, email, selected_group)
                    if success:
                        group_added += 1
            except ClientError:
                failed += 1

        msg = f"Created: {created}, Failed/Skipped: {failed}"
        if selected_group:
            msg += f", Added to group: {group_added}"
        status.set_message(msg)
        self.query_one("#num-users", Input).value = ""
        bulk_group_select.value = Select.BLANK

    @on(Button.Pressed, "#back")
    def go_back(self) -> None:
        """Return to main menu."""
        self.app.pop_screen()


class UsersScreen(Screen):
    """Screen for listing, viewing, editing, and deleting users."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("v", "view_user", "View"),
        Binding("e", "edit_user", "Edit"),
        Binding("d", "delete_selected", "Delete"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Vertical(
                Label("User Management", classes="title"),
                Horizontal(
                    Button("Refresh", id="refresh", variant="primary"),
                    Button("View", id="view", variant="default"),
                    Button("Edit", id="edit", variant="warning"),
                    Button("Delete Selected", id="delete-selected", variant="error"),
                    Button("Delete All", id="delete-all", variant="error"),
                    Button("Back", id="back"),
                    classes="button-row",
                ),
                DataTable(id="users-table"),
                StatusBar(id="status"),
                classes="table-container",
            ),
            id="users-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the data table."""
        table = self.query_one("#users-table", DataTable)
        table.add_column("Select", key="select")
        table.add_column("Username", key="username")
        table.add_column("Email", key="email")
        table.add_column("Status", key="status")
        table.add_column("Enabled", key="enabled")
        table.add_column("Created", key="created")
        table.cursor_type = "row"
        self.selected_users: set[str] = set()
        self.load_users()

    def load_users(self) -> None:
        """Load users from Cognito."""
        table = self.query_one("#users-table", DataTable)
        status = self.query_one("#status", StatusBar)
        table.clear()
        self.selected_users.clear()

        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        try:
            client = get_cognito_client()
            excluded = set(get_excluded_users())
            pagination_token = None
            users = []

            while True:
                kwargs = {"UserPoolId": user_pool_id}
                if pagination_token:
                    kwargs["PaginationToken"] = pagination_token

                response = client.list_users(**kwargs)

                for user in response["Users"]:
                    username = user["Username"]
                    email = ""
                    for attr in user.get("Attributes", []):
                        if attr["Name"] == "email":
                            email = attr["Value"]
                            break

                    user_status = user.get("UserStatus", "UNKNOWN")
                    enabled = "Yes" if user.get("Enabled", False) else "No"
                    created = user.get("UserCreateDate", "")
                    if created:
                        created = created.strftime("%Y-%m-%d %H:%M")

                    is_excluded = username in excluded or email in excluded
                    select_marker = "[E]" if is_excluded else "[ ]"

                    users.append((select_marker, username, email, user_status, enabled, created))

                pagination_token = response.get("PaginationToken")
                if not pagination_token:
                    break

            for user_data in users:
                table.add_row(*user_data)

            status.set_message(f"Loaded {len(users)} users")

        except ClientError as e:
            status.set_message(f"Error loading users: {e}", error=True)

    def get_selected_row_username(self) -> str | None:
        """Get username from currently highlighted row."""
        table = self.query_one("#users-table", DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key
            row_data = table.get_row(row_key)
            return row_data[1]  # Username column
        return None

    @on(DataTable.RowSelected)
    def toggle_selection(self, event: DataTable.RowSelected) -> None:
        """Toggle user selection."""
        table = self.query_one("#users-table", DataTable)
        row_key = event.row_key

        if row_key is None:
            return

        row_data = table.get_row(row_key)
        username = row_data[1]
        current_select = row_data[0]

        # Don't allow selecting excluded users
        if current_select == "[E]":
            return

        if username in self.selected_users:
            self.selected_users.remove(username)
            new_select = "[ ]"
        else:
            self.selected_users.add(username)
            new_select = "[X]"

        table.update_cell(row_key, "select", new_select)

    @on(Button.Pressed, "#refresh")
    def action_refresh(self) -> None:
        """Refresh the user list."""
        self.load_users()

    @on(Button.Pressed, "#view")
    def action_view_user(self) -> None:
        """View selected user details."""
        status = self.query_one("#status", StatusBar)
        username = self.get_selected_row_username()

        if not username:
            status.set_message("No user selected", error=True)
            return

        self.app.push_screen(ViewUserScreen(username))

    @on(Button.Pressed, "#edit")
    def action_edit_user(self) -> None:
        """Edit selected user."""
        status = self.query_one("#status", StatusBar)
        username = self.get_selected_row_username()

        if not username:
            status.set_message("No user selected", error=True)
            return

        self.app.push_screen(EditUserScreen(username))

    @on(Button.Pressed, "#delete-selected")
    def action_delete_selected(self) -> None:
        """Delete selected users."""
        status = self.query_one("#status", StatusBar)

        if not self.selected_users:
            status.set_message("No users selected (use Enter to select)", error=True)
            return

        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        try:
            client = get_cognito_client()
            deleted = 0

            for username in list(self.selected_users):
                client.admin_delete_user(
                    UserPoolId=user_pool_id,
                    Username=username,
                )
                deleted += 1

            status.set_message(f"Deleted {deleted} users")
            self.load_users()

        except ClientError as e:
            status.set_message(f"Error deleting users: {e}", error=True)

    @on(Button.Pressed, "#delete-all")
    def delete_all_users(self) -> None:
        """Delete all users except excluded ones."""
        status = self.query_one("#status", StatusBar)

        user_pool_id = get_user_pool_id()
        if not user_pool_id:
            status.set_message("Error: User Pool ID not configured", error=True)
            return

        try:
            client = get_cognito_client()
            excluded = set(get_excluded_users())
            pagination_token = None
            deleted = 0
            skipped = 0

            while True:
                kwargs = {"UserPoolId": user_pool_id}
                if pagination_token:
                    kwargs["PaginationToken"] = pagination_token

                response = client.list_users(**kwargs)

                for user in response["Users"]:
                    username = user["Username"]
                    email = ""
                    for attr in user.get("Attributes", []):
                        if attr["Name"] == "email":
                            email = attr["Value"]
                            break

                    if username in excluded or email in excluded:
                        skipped += 1
                        continue

                    client.admin_delete_user(
                        UserPoolId=user_pool_id,
                        Username=username,
                    )
                    deleted += 1

                pagination_token = response.get("PaginationToken")
                if not pagination_token:
                    break

            status.set_message(f"Deleted: {deleted}, Skipped: {skipped} (excluded)")
            self.load_users()

        except ClientError as e:
            status.set_message(f"Error deleting users: {e}", error=True)

    @on(Button.Pressed, "#back")
    def go_back(self) -> None:
        """Return to main menu."""
        self.app.pop_screen()


class SettingsScreen(Screen):
    """Screen for viewing/editing settings."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            VerticalScroll(
                Label("Settings", classes="title"),
                Label("Current Configuration", classes="subtitle"),
                Static(id="config-display"),
                Label("", classes="separator"),
                Label("Note: Settings are read from environment variables or .env file.", classes="note"),
                Label("Restart the application after modifying .env", classes="note"),
                Horizontal(
                    Button("Back", id="back"),
                    classes="button-row",
                ),
                classes="settings-container",
            ),
            id="settings-outer",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Display current configuration."""
        from .config import get_aws_config

        config = get_aws_config()
        user_pool_id = get_user_pool_id()
        excluded_users = get_excluded_users()

        config_text = f"""AWS Region: {config.get('region_name', 'Not set')}
AWS Access Key ID: {'*' * 16 + config.get('aws_access_key_id', '')[-4:] if config.get('aws_access_key_id') else 'Not set'}
User Pool ID: {user_pool_id or 'Not set'}
Excluded Users: {', '.join(excluded_users) if excluded_users else 'None'}
"""
        self.query_one("#config-display", Static).update(config_text)

    @on(Button.Pressed, "#back")
    def go_back(self) -> None:
        """Return to main menu."""
        self.app.pop_screen()


class MainMenuScreen(Screen):
    """Main menu screen."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Vertical(
                Label("AWS Cognito User Manager", classes="app-title"),
                Label("", classes="separator"),
                Button("Create Users", id="create", variant="primary"),
                Button("Manage Users", id="users", variant="primary"),
                Button("Settings", id="settings"),
                Button("Quit", id="quit", variant="error"),
                classes="menu-container",
            ),
            id="main-container",
        )
        yield Footer()

    @on(Button.Pressed, "#create")
    def show_create_screen(self) -> None:
        """Show the create user screen."""
        self.app.push_screen(CreateUserScreen())

    @on(Button.Pressed, "#users")
    def show_users_screen(self) -> None:
        """Show the users screen."""
        self.app.push_screen(UsersScreen())

    @on(Button.Pressed, "#settings")
    def show_settings_screen(self) -> None:
        """Show the settings screen."""
        self.app.push_screen(SettingsScreen())

    @on(Button.Pressed, "#quit")
    def quit_app(self) -> None:
        """Quit the application."""
        self.app.exit()


class CognitoUserApp(App):
    """Main Cognito User Management TUI Application."""

    TITLE = "AWS Cognito User Manager"
    CSS = """
    Screen {
        align: center middle;
    }

    #main-container {
        width: 60;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: thick $primary;
    }

    #create-container, #users-container, #settings-outer, #view-container, #edit-outer {
        width: 90%;
        height: 90%;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    .menu-container {
        align: center middle;
        height: auto;
    }

    .menu-container Button {
        width: 100%;
        margin: 1 0;
    }

    .app-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding: 1 0;
        width: 100%;
    }

    .title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding: 1 0;
        width: 100%;
    }

    .subtitle {
        text-style: bold;
        color: $secondary;
        padding: 1 0;
    }

    .separator {
        height: 1;
    }

    .form-container, .details-container, .edit-container {
        padding: 1 2;
    }

    .form-row {
        height: 3;
        margin: 1 0;
    }

    .form-row Label {
        width: 20;
        padding: 1 1;
    }

    .form-row Input {
        width: 1fr;
    }

    .form-row Select {
        width: 1fr;
    }

    .form-row Static {
        width: 1fr;
        padding: 1 1;
    }

    .checkbox-row {
        height: 3;
        margin: 1 0;
        padding: 0 1;
    }

    .checkbox-row Checkbox {
        margin-right: 4;
    }

    .button-row {
        height: auto;
        margin: 1 0;
        align: center middle;
    }

    .button-row Button {
        margin: 0 1;
    }

    .table-container {
        height: 100%;
    }

    .table-container DataTable {
        height: 1fr;
        margin: 1 0;
    }

    .settings-container {
        padding: 1 2;
    }

    #config-display, #user-details, #user-attributes {
        padding: 1 2;
        background: $surface-darken-1;
        border: round $primary;
        margin: 1 0;
    }

    .note {
        color: $text-muted;
        text-style: italic;
        padding: 0 0 0 1;
    }

    StatusBar {
        height: 2;
        padding: 0 1;
        background: $surface-darken-1;
        margin: 1 0;
    }

    StatusBar.error {
        color: $error;
    }

    .label {
        width: 20;
    }

    Button.warning {
        background: $warning;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        """Show the main menu on startup."""
        self.push_screen(MainMenuScreen())


def main():
    """Entry point for the TUI application."""
    app = CognitoUserApp()
    app.run()


if __name__ == "__main__":
    main()
