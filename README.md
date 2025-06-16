Absolutely — here’s the complete, copy-pasteable `README.md` content in one continuous message, with no formatting interruptions:

---

```markdown
# NoleBot-V3

NoleBot-V3 is a modular Discord bot developed for the FSU Esports community. It is designed to automate student verification, facilitate custom role assignments, and support future event and calendar integration. The project is structured for clarity and scalability, making it easy for other developers to contribute, review, or expand its capabilities.

## Project Overview

This bot is built using the `discord.py` library with full slash command support. Its architecture is cog-based, allowing each feature to be developed and maintained independently. The project also includes a separate utility script for polling form submissions and assigning verification codes.

## Features

### Student Verification System

The verification system is designed to authenticate FSU students using a Google Form. When a student submits the form, a background polling script (`form_verification_poller.py`) periodically checks for new submissions. Upon detecting one, it:

1. Generates a unique, time-limited verification code
2. Stores this code in a queue (`json/dm_queue.json`)
3. The bot reads from this queue and sends the code to the corresponding Discord user
4. When the user sends the code using a slash command (e.g., `/verify ABC123`), the bot checks it against the stored data and assigns the appropriate role if valid

Verification codes are case-sensitive, expire after 72 hours, and are single-use.

### Cog Modules

#### `calendar_cog.py`

This cog will handle future integration with an external calendar (e.g., Outlook or Google Calendar). It is intended to fetch events and potentially announce them in a Discord channel. This module is currently under construction, but the structure is in place for future deployment once authenticated access is configured.

#### `gm_role_assignment.py`

This cog enables users to self-assign roles via slash commands. The roles are defined in `json/assignable_roles.json`, allowing server admins to configure which roles can be selected by users. Commands include the ability to join or leave a role, and feedback is provided to the user upon success or failure.

## File Structure

```

NoleBot-V3/
├── cogs/                          # Feature modules (cogs)
│   ├── calendar\_cog.py
│   └── gm\_role\_assignment.py
│
├── json/                          # Persistent data storage
│   ├── assignable\_roles.json
│   ├── poll\_state.json
│   ├── verified.json              # Excluded from Git
│   └── verified\_backup.json       # Excluded from Git
│
├── utils/
│   └── form\_verification\_poller.py   # Polls Google Form and assigns codes
│
├── bot.py                        # Main Discord bot entry point
├── requirements.txt              # Dependency list
├── .env                          # Contains API keys and tokens (excluded)
├── .gitignore                    # Prevents sensitive files from being pushed
└── README.md                     # Project documentation

````

## Setup Instructions

1. **Clone the repository**

```bash
git clone https://github.com/kquessen/NoleBotV3.git
cd NoleBotV3
````

2. **Create a `.env` file** with the following structure:

```
DISCORD_TOKEN=your_discord_bot_token
SERVER_ID=your_discord_server_id
VERIFIED_STUDENT_ROLE_ID=role_id_to_assign
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run the bot**

```bash
python bot.py
```

5. **(Optional) Run the verification poller in parallel**

This script should be run in a separate process (or via a background task manager):

```bash
python utils/form_verification_poller.py
```

## Notes

* The bot is still under active development. Some modules are incomplete or placeholders for future features.
* Sensitive files, including `.env`, log files, and certain JSON datasets, are excluded from version control using `.gitignore`.
* Contributors are welcome to suggest improvements, open issues, or submit pull requests.

## Contact

For questions, concerns, or collaboration inquiries, please reach out to **Kailee Quessenberry** directly.

```
```
