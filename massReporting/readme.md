# 🚨 Telegram Report Tool (Educational)

This tool allows a user to **report a Telegram user, group, or channel** using the [Telethon](https://github.com/LonamiWebs/Telethon) library. It supports multiple official Telegram reporting reasons (e.g., spam, violence, child abuse, etc.).

⚠️ **DISCLAIMER**  
This script is provided **strictly for educational purposes** only.  
**Misusing this tool to falsely report users or groups violates Telegram’s Terms of Service** and **may result in permanent account suspension or legal consequences**. Use responsibly and only for testing on your own groups/accounts.

---

## 📦 Features

- Login with your Telegram number (2FA supported).
- Select report reason from official Telegram categories.
- Specify number of times to report (1–10).
- Random delay to simulate human behavior.
- Auto-handles FloodWait errors.

---

## 📥 Installation

1. **Clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/tools
cd tools/massReporting
```

2. **Install dependencies**

Make sure you have Python 3.7+ installed.

```bash
pip install -r requirements.txt
```

3. **Configure your Telegram API credentials**

- Visit [my.telegram.org](https://my.telegram.org)
- Login and create a new application to get your `API_ID` and `API_HASH`
- Replace them inside the script:
  ```python
  API_ID = YOUR_API_ID
  API_HASH = "YOUR_API_HASH"
  ```

---

## ▶️ Usage

```bash
python3 massReporting.py
```

Then follow the prompts:

- Enter your phone number.
- Choose the report reason.
- Enter the username/group to report.
- Specify the number of times to send the report.

---

## ⚠️ Warning

> ✅ Educational only — do not misuse.  
> ❌ Sending false reports is **strictly against Telegram policies**.  
> ❌ Use it only on test accounts/groups you own or have permission to test.  
> ✅ Always respect legal and ethical boundaries when working with security tools.

---

