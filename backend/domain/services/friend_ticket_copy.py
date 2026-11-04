"""
Wording of the "bring a friend" emails. Marketing can edit this file freely.

Placeholders, filled in when the email is sent (keep the curly braces):
  {buyer}  the buyer's name          {friend}  the friend's name, or their email
  {event}  the event name            {date}    the event date and time
  {email}  the friend's email address

Each email has a subject, a header (the coloured bar at the top), a heading,
paragraphs, and one button. The website's wording is in
frontend/src/content/bringAFriend.js.
"""

# To the friend when they don't have an account yet: one action, sign up.
FRIEND_INVITED = {
    "subject": "{buyer} got you a ticket to {event}",
    "header": "You've got a ticket",
    "heading": "{buyer} got you a ticket",
    "paragraphs": [
        "{buyer} bought two tickets to {event} on {date}, and one of them is yours. It's already paid for.",
        "To get it, create your Ennova account with this email address ({email}). It takes a minute.",
    ],
    "button": "Get my ticket",
    "footer": "This link is just for you. If you weren't expecting it, you can ignore this email.",
}

# To the friend when the email already has an account: nothing to do.
FRIEND_ASSIGNED = {
    "subject": "{buyer} got you a ticket to {event}",
    "header": "You've got a ticket",
    "heading": "{buyer} got you a ticket",
    "paragraphs": [
        "{buyer} bought two tickets to {event} on {date}, and one of them is yours. It's already paid for.",
        "It's in your Ennova account now. There's nothing else to do: just bring your ticket on the day.",
    ],
    "button": "View my ticket",
    "footer": "",
}

# To the friend, three days after the link went out, if they haven't claimed.
FRIEND_REMINDER = {
    "subject": "Your ticket to {event} is waiting",
    "header": "Your ticket is waiting",
    "heading": "Don't forget your ticket",
    "paragraphs": [
        "{buyer} got you a ticket to {event} on {date}, but you haven't picked it up yet.",
        "Create your Ennova account with {email} and it's yours.",
    ],
    "button": "Get my ticket",
    "footer": "This link is just for you.",
}

# To the buyer when the friend claims through the link.
BUYER_FRIEND_CLAIMED = {
    "subject": "{friend} has their ticket to {event}",
    "header": "Your friend is in",
    "heading": "{friend} has their ticket",
    "paragraphs": [
        "{friend} picked up the ticket you got them for {event}. See you both on {date}!",
    ],
    "button": "View my ticket",
    "footer": "",
}

# To the buyer when the friend turns out to have their own ticket already.
BUYER_FRIEND_ALREADY_REGISTERED = {
    "subject": "Your second ticket to {event} needs a new owner",
    "header": "Choose someone else",
    "heading": "{email} already has a ticket",
    "paragraphs": [
        "{email} is already registered for {event}, so we couldn't give them the ticket you bought.",
        "You can send it to someone else from your ticket page.",
    ],
    "button": "Choose someone else",
    "footer": "",
}
