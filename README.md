**NoleBot-V3**

NoleBot-V3 is a Discord bot built for the FSU Esports server. It handles student verification through a Google Form, lets game managers assign team roles, and is structured to support future features like calendar event announcements. The bot is organized for easy updates and long-term maintenance. Individual instructions of how to trouble-shoot code or common issues may be found in the specific 

**Project Overview**

The bot uses the `discord.py` library and supports slash commands only with /verify. Attempts to use /verify in anything but DMs are rejected silently. Each major function is contained in a separate cog module. There's also a separate utility script that runs in the background to handle form submissions and queue verification codes.

**Student Verification System**

The student verification process is automated using a Google Form. A background script, `form_verification_poller.py`, checks the form for new submissions. When a new response is detected, the script generates a verification code, stores it in a shared queue, and the bot emails that code to the corresponding user. Users then use a slash command (e.g. `/verify ABC123`) in Discord DMs to confirm the code and receive the verified student role. Codes are case-sensitive, expire after 72 hours, and can only be used once. A backup file stores verification history in case anything goes wrong.

**Cog Modules**

* **calendar\_cog.py** – Placeholder for future calendar integration. This module is set up to eventually pull events from the offical FSU Esports Outlook and post them in a Discord channel. It will ping a role which users can opt into receiving when they join the server, once 5 days before the event, and once the morning of the event (9am).

* **gm\_role\_assignment.py** – Handles assignable roles for game managers. These commands can only be used in #gms-assign-here by people with authorized role IDs (found in assignable_roles.json). If there is an issue with a role not being authorized to use these commands, double check that the role in question's ID is listed under "authorized_roles." If there is an issue with a role not being able to be assigned to a user, double check that the role in question's ID is listed under "assignable_roles." Role IDs can be found via opening Discord in developer mode and right clicking on the role in Server Settings -> Roles -> Right Click Role -> Copy Role ID.

**Notes**

Sensitive files like `.env`, credential keys, and user data are excluded from the repository. This bot is intended specifically for the FSU Esports server and is not meant for public distribution. If you have questions or want to report an issue, please reach out to Kailee Quessenberry directly.

