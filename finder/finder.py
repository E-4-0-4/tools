import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import messagebox, filedialog
import pandas as pd

# List of platforms and their URL formats
platforms = {
    "GitHub": "https://github.com/{}",
    "Twitter": "https://twitter.com/{}",
    "Instagram": "https://www.instagram.com/{}",
    "Facebook": "https://www.facebook.com/{}",
    "Reddit": "https://www.reddit.com/user/{}",
    "Pinterest": "https://www.pinterest.com/{}",
    "TikTok": "https://www.tiktok.com/@{}",
    "YouTube": "https://www.youtube.com/{}",
    "LinkedIn": "https://www.linkedin.com/in/{}",
    "Medium": "https://medium.com/@{}",
    "Quora": "https://www.quora.com/profile/{}",
    "StackOverflow": "https://stackoverflow.com/users/{}",
    "DeviantArt": "https://www.deviantart.com/{}",
    "Behance": "https://www.behance.net/{}",
    "Dribbble": "https://dribbble.com/{}",
    "Flickr": "https://www.flickr.com/photos/{}",
    "Vimeo": "https://vimeo.com/{}",
    "SoundCloud": "https://soundcloud.com/{}",
    "Spotify": "https://open.spotify.com/user/{}",
    "Twitch": "https://www.twitch.tv/{}",
    "Steam": "https://steamcommunity.com/id/{}",
    "Etsy": "https://www.etsy.com/shop/{}",
    "Bandcamp": "https://{}.bandcamp.com",
    "Wattpad": "https://www.wattpad.com/user/{}",
    "Goodreads": "https://www.goodreads.com/user/show/{}",
    "Smule": "https://www.smule.com/{}",
    "Anchor": "https://anchor.fm/{}",
    "Mixcloud": "https://www.mixcloud.com/{}",
    "CodePen": "https://codepen.io/{}",
    "GitLab": "https://gitlab.com/{}",
    "Bitbucket": "https://bitbucket.org/{}",
    "Figma": "https://www.figma.com/@{}",
    "Notion": "https://www.notion.so/{}",
    "Canva": "https://www.canva.com/{}",
    "Trello": "https://trello.com/{}",
    "Asana": "https://app.asana.com/0/{}",
    "Slack": "https://{}.slack.com",
    "Discord": "https://discord.com/users/{}",
    "Telegram": "https://t.me/{}",
    "WhatsApp": "https://wa.me/{}",
    "Signal": "https://signal.org/en/download/",
    "Keybase": "https://keybase.io/{}",
    "HackerNews": "https://news.ycombinator.com/user?id={}",
    "ProductHunt": "https://www.producthunt.com/@{}",
    "AngelList": "https://angel.co/{}",
    "Crunchbase": "https://www.crunchbase.com/person/{}",
}

# Function to check if a profile exists on a platform
def check_profile(platform, username):
    url = platforms[platform].format(username)
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return url
        else:
            return None
    except requests.RequestException:
        return None

def search_username(username):
    results = {}
    for platform in platforms:
        print(f"Checking {platform}...")
        profile_url = check_profile(platform, username)
        if profile_url:
            results[platform] = profile_url
        else:
            results[platform] = None
    return results

def export_results(results, file_type):
    if file_type == "csv":
        df = pd.DataFrame(list(results.items()), columns=['Platform', 'URL'])
        df.to_csv('results.csv', index=False)
        messagebox.showinfo("Export", "Results exported to results.csv")
    elif file_type == "txt":
        with open('results.txt', 'w') as f:
            for platform, url in results.items():
                f.write(f"{platform}: {url}\n")
        messagebox.showinfo("Export", "Results exported to results.txt")

class OSINTTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OSINT Username Finder")
        self.geometry("600x400")

        self.username_label = tk.Label(self, text="Enter Username:")
        self.username_label.pack(pady=10)

        self.username_entry = tk.Entry(self, width=50)
        self.username_entry.pack(pady=10)

        self.search_button = tk.Button(self, text="Search", command=self.search)
        self.search_button.pack(pady=10)

        self.result_text = tk.Text(self, height=20, width=70)
        self.result_text.pack(pady=10)

        self.export_button = tk.Button(self, text="Export Results", command=self.export)
        self.export_button.pack(pady=10)

    def search(self):
        username = self.username_entry.get()
        if not username:
            messagebox.showwarning("Warning", "Please enter a username.")
            return

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "Searching...\n")
        self.update_idletasks()

        results = search_username(username)
        for platform, url in results.items():
            if url:
                self.result_text.insert(tk.END, f"{platform}: {url}\n")
            else:
                self.result_text.insert(tk.END, f"{platform}: Not found\n")

    def export(self):
        file_type = filedialog.askstring("Export", "Enter file type (csv or txt):")
        if file_type not in ["csv", "txt"]:
            messagebox.showwarning("Warning", "Invalid file type. Please enter 'csv' or 'txt'.")
            return

        results = {}
        for line in self.result_text.get("1.0", tk.END).strip().split("\n"):
            if ": " in line:
                platform, url = line.split(": ")
                results[platform] = url

        export_results(results, file_type)

if __name__ == "__main__":
    app = OSINTTool()
    app.mainloop()