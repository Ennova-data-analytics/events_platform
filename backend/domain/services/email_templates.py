from jinja2 import Template


def get_base_template() -> str:
    """Base HTML template for emails"""
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #13182e;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }
        .content {
            background-color: #f9f9f9;
            padding: 30px;
            border: 1px solid #ddd;
            border-radius: 0 0 5px 5px;
        }
        .button {
            display: inline-block;
            padding: 12px 24px;
            background-color: #13182e;
            color: white !important;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
        }
        .button:hover {
            background-color: #1a2038;
        }
        .footer {
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }
        .event-details {
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ header_title }}</h1>
    </div>
    <div class="content">
        {{ content }}
    </div>
    <div class="footer">
        <p>This is an automated message from Events Platform</p>
        <p>Please do not reply to this email</p>
    </div>
</body>
</html>
"""


def render_registration_approved_email(
    user_name: str,
    event_name: str,
    event_date: str,
    event_location: str,
    price: float = None,
    event_url: str = None
) -> tuple[str, str]:
    """
    Render registration approved email

    Returns:
        Tuple of (html_content, text_content)
    """
    content = f"""
        <h2>Congratulations, {user_name}! 🎉</h2>
        <p>Your registration for <strong>{event_name}</strong> has been approved!</p>

        <div class="event-details">
            <h3>Event Details</h3>
            <p><strong>Event:</strong> {event_name}</p>
            <p><strong>Date:</strong> {event_date}</p>
            <p><strong>Location:</strong> {event_location}</p>
            {"<p><strong>Price:</strong> €" + f"{price:.2f}" + "</p>" if price and price > 0 else ""}
        </div>

        {"<p>Please complete your payment of €" + f"{price:.2f}" + " to confirm your spot.</p>" if price and price > 0 else "<p>Your spot is confirmed! We look forward to seeing you there.</p>"}

        {f'<a href="{event_url}" class="button">View Event Details</a>' if event_url else ""}

        <p>If you have any questions, please don't hesitate to contact us.</p>
    """

    base = Template(get_base_template())
    html_content = base.render(
        header_title="Registration Approved",
        content=content
    )

    text_content = f"""
Registration Approved

Congratulations, {user_name}!

Your registration for {event_name} has been approved!

Event Details:
- Event: {event_name}
- Date: {event_date}
- Location: {event_location}
{"- Price: €" + f"{price:.2f}" if price and price > 0 else ""}

{"Please complete your payment of €" + f"{price:.2f}" + " to confirm your spot." if price and price > 0 else "Your spot is confirmed! We look forward to seeing you there."}

{f"View event: {event_url}" if event_url else ""}

If you have any questions, please don't hesitate to contact us.
"""

    return html_content, text_content


def render_registration_rejected_email(
    user_name: str,
    event_name: str,
    reason: str = None
) -> tuple[str, str]:
    """Render registration rejected email"""
    content = f"""
        <h2>Registration Update</h2>
        <p>Dear {user_name},</p>
        <p>Thank you for your interest in <strong>{event_name}</strong>.</p>
        <p>Unfortunately, your registration was not approved at this time.</p>
        {"<p><strong>Reason:</strong> " + reason + "</p>" if reason else ""}
        <p>We appreciate your interest and encourage you to register for future events.</p>
    """

    base = Template(get_base_template())
    html_content = base.render(
        header_title="Registration Update",
        content=content
    )

    text_content = f"""
Registration Update

Dear {user_name},

Thank you for your interest in {event_name}.

Unfortunately, your registration was not approved at this time.

{"Reason: " + reason if reason else ""}

We appreciate your interest and encourage you to register for future events.
"""

    return html_content, text_content


def render_registration_received_email(
    user_name: str,
    event_name: str,
    event_date: str
) -> tuple[str, str]:
    """Render registration received confirmation email"""
    content = f"""
        <h2>Registration Received ✓</h2>
        <p>Dear {user_name},</p>
        <p>We have received your registration for <strong>{event_name}</strong>.</p>
        <p>Your application is currently pending approval. We will notify you once it has been reviewed.</p>

        <div class="event-details">
            <p><strong>Event:</strong> {event_name}</p>
            <p><strong>Date:</strong> {event_date}</p>
        </div>

        <p>Thank you for your interest!</p>
    """

    base = Template(get_base_template())
    html_content = base.render(
        header_title="Registration Received",
        content=content
    )

    text_content = f"""
Registration Received

Dear {user_name},

We have received your registration for {event_name}.

Your application is currently pending approval. We will notify you once it has been reviewed.

Event: {event_name}
Date: {event_date}

Thank you for your interest!
"""

    return html_content, text_content


def render_payment_confirmed_email(
    user_name: str,
    event_name: str,
    event_date: str,
    event_location: str,
    price: float,
    event_url: str = None
) -> tuple[str, str]:
    """
    Render payment confirmation email

    Returns:
        Tuple of (html_content, text_content)
    """
    content = f"""
        <h2>Payment Confirmed! 🎉</h2>
        <p>Hi {user_name},</p>
        <p>Great news! Your payment of <strong>€{price:.2f}</strong> has been successfully processed.</p>

        <div class="event-details">
            <h3>Event Details</h3>
            <p><strong>Event:</strong> {event_name}</p>
            <p><strong>Date:</strong> {event_date}</p>
            <p><strong>Location:</strong> {event_location}</p>
            <p><strong>Amount Paid:</strong> €{price:.2f}</p>
        </div>

        <p>Your spot is now confirmed! We look forward to seeing you there.</p>

        {f'<a href="{event_url}" class="button">View Event Details</a>' if event_url else ""}

        <p>If you have any questions, please contact us.</p>
    """

    base = Template(get_base_template())
    html_content = base.render(
        header_title="Payment Confirmed",
        content=content
    )

    text_content = f"""
Payment Confirmed!

Hi {user_name},

Great news! Your payment of €{price:.2f} has been successfully processed.

Event Details:
- Event: {event_name}
- Date: {event_date}
- Location: {event_location}
- Amount Paid: €{price:.2f}

Your spot is now confirmed! We look forward to seeing you there.

{f"View event: {event_url}" if event_url else ""}

If you have any questions, please contact us.
"""

    return html_content, text_content


def render_password_reset_email(
    user_name: str,
    reset_url: str
) -> tuple[str, str]:
    """
    Render password reset email
    
    Returns:
        Tuple of (html_content, text_content)
    """
    content = f"""
        <h2>Password Reset Request</h2>
        <p>Hi {user_name},</p>
        <p>We received a request to reset your password for your Events Platform account.</p>
        <p>Click the button below to reset your password. This link will expire in <strong>1 hour</strong>.</p>
        
        <a href="{reset_url}" class="button">Reset Password</a>
        
        <p>If you didn't request this password reset, you can safely ignore this email. Your password will remain unchanged.</p>
        
        <p>For security reasons, this link can only be used once.</p>
        
        <p style="color: #666; font-size: 12px; margin-top: 20px;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            {reset_url}
        </p>
    """
    
    base = Template(get_base_template())
    html_content = base.render(
        header_title="Password Reset",
        content=content
    )
    
    text_content = f"""
Password Reset Request

Hi {user_name},

We received a request to reset your password for your Events Platform account.

Click the link below to reset your password. This link will expire in 1 hour.

{reset_url}

If you didn't request this password reset, you can safely ignore this email. Your password will remain unchanged.

For security reasons, this link can only be used once.
"""
    
    return html_content, text_content