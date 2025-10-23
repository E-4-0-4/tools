Markdown
Code
Preview
# RamBaan – human-friendly ZIP / RAR password cracker  
*(everything stays in `~/ramBaan`)*

## DISCLAIMER
This tool is for **EDUCATIONAL and LEGITIMATE PENETRATION-TESTING** purposes only.  
Cracking archives you do **NOT own** or do **NOT have explicit permission** to test is **ILLEGAL** in most jurisdictions.  
The authors assume **NO LIABILITY** for misuse. **USE RESPONSIBLY – OBEY LOCAL LAWS.**

---

## 1-LINE INSTALL
```bash
wget -O ~/ramBaan https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/ramBaan && chmod +x ~/ramBaan




QUICK CHEAT-SHEET



# Dictionary (rockyou)
~/ramBaan secret.zip --dict rockyou

# Your own word-list
~/ramBaan file.rar --dict -listBrute /tmp/mywords.txt

# Human mask: 1 upper, 3 lower, 2 digits, 1 symbol
~/ramBaan zipfile --mask uppercase lowercase(3) number(2) specialCharacter

# Range mask: uppercase(A-E) + digits 0-3 + !@#
~/ramBaan file.zip --mask uppercase(A-E) number(0-3) specialCharacter(!@#)

# Brute 1-8 alnum
~/ramBaan stuff.rar --incr Alnum 8

# Show cracked password
~/ramBaan file.zip --show

# Extract once you know the password
~/ramBaan file.zip --extract MyP@ss




# Dictionary → big mask → incremental (auto-stop when cracked)
# Run inside tmux/screen – will take time!
~/ramBaan target.zip --dict rockyou \
  && ~/ramBaan target.zip --mask uppercase lowercase(3) number(2) specialCharacter \
  && ~/ramBaan target.zip --incr All 10


mask keyword    

| Keyword            | Default      | Example                              |
| ------------------ | ------------ | ------------------------------------ |
| `uppercase`        | A-Z          | `uppercase(A-E)` → only A B C D E    |
| `lowercase`        | a-z          | `lowercase(a-f)` → a b c d e f       |
| `number`           | 0-9          | `number(0-3)` → 0 1 2 3              |
| `specialCharacter` | !@#\$%^&\*() | `specialCharacter(!@#)` → only ! @ # |


output locations 


~/ramBaan/rockyou.txt                 – word-list (auto-downloaded)
~/ramBaan/<archive_name>.hash         – john hash file
~/ramBaan/extracted_<archive_name>/   – extracted contents (after --extract)
~/ramBaan/john.pot                    – cracked passwords (john pot-file)


    Markdown
Copy
Code
Preview
# RamBaan – human-friendly ZIP / RAR password cracker  
*(everything stays in `~/ramBaan`)*

## DISCLAIMER
This tool is for **EDUCATIONAL and LEGITIMATE PENETRATION-TESTING** purposes only.  
Cracking archives you do **NOT own** or do **NOT have explicit permission** to test is **ILLEGAL** in most jurisdictions.  
The authors assume **NO LIABILITY** for misuse. **USE RESPONSIBLY – OBEY LOCAL LAWS.**

---

## 1-LINE INSTALL
```bash
wget -O ~/ramBaan https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/ramBaan && chmod +x ~/ramBaan
QUICK CHEAT-SHEET
bash
Copy
# Dictionary (rockyou)
~/ramBaan secret.zip --dict rockyou

# Your own word-list
~/ramBaan file.rar --dict -listBrute /tmp/mywords.txt

# Human mask: 1 upper, 3 lower, 2 digits, 1 symbol
~/ramBaan zipfile --mask uppercase lowercase(3) number(2) specialCharacter

# Range mask: uppercase(A-E) + digits 0-3 + !@#
~/ramBaan file.zip --mask uppercase(A-E) number(0-3) specialCharacter(!@#)

# Brute 1-8 alnum
~/ramBaan stuff.rar --incr Alnum 8

# Show cracked password
~/ramBaan file.zip --show

# Extract once you know the password
~/ramBaan file.zip --extract MyP@ss
AGGRESSIVE “TRY-EVERYTHING” COMMAND
bash
Copy
# Dictionary → big mask → incremental (auto-stop when cracked)
# Run inside tmux/screen – will take time!
~/ramBaan target.zip --dict rockyou \
  && ~/ramBaan target.zip --mask uppercase lowercase(3) number(2) specialCharacter \
  && ~/ramBaan target.zip --incr All 10
MASK KEYWORDS
Table
Copy
Keyword	Default	Example
uppercase	A-Z	uppercase(A-E) → only A B C D E
lowercase	a-z	lowercase(a-f) → a b c d e f
number	0-9	number(0-3) → 0 1 2 3
specialCharacter	!@#$%^&*()	specialCharacter(!@#) → only ! @ #
OUTPUT LOCATIONS
Copy
~/ramBaan/rockyou.txt                 – word-list (auto-downloaded)
~/ramBaan/<archive_name>.hash         – john hash file
~/ramBaan/extracted_<archive_name>/   – extracted contents (after --extract)
~/ramBaan/john.pot                    – cracked passwords (john pot-file)
TIPS
Run inside tmux or screen for long jobs.
Use --show to print only the password once cracked.
Smaller masks/ranges = faster cracks.
Keep word-lists in ~/ramBaan/ for quick reference.
Always respect privacy and ownership laws.
