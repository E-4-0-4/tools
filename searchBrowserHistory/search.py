#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search_my_history.py  –  Advanced personal history search with GUI (Cross-platform: Windows, Linux, macOS)
Supports: Chrome, Edge, Brave, Chromium, Firefox, LibreWolf
Features:
- Cross-platform support
- GUI with search, browser/date filters, and JSON/CSV export
- Double-click URL to open in default browser
- Deduplication of URLs, keeping the most recent
"""
from __future__ import annotations
import sqlite3
import os
import sys
import pathlib
import json
import csv
import shutil
import tempfile
import glob
import platform
import webbrowser
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.constants import END

  
# 1. Browser profile globs per platform
  
def get_browser_profile_globs() -> dict:
    """Return browser history file globs based on the current OS."""
    system = platform.system()
    home = pathlib.Path.home()
    
    if system == "Windows":
        local_appdata = pathlib.Path(os.environ.get("LOCALAPPDATA", ""))
        appdata_roaming = pathlib.Path(os.environ.get("APPDATA", ""))
        return {
            "chrome":   local_appdata / "Google/Chrome/User Data/*/History",
            "edge":     local_appdata / "Microsoft/Edge/User Data/*/History",
            "brave":    local_appdata / "BraveSoftware/Brave-Browser/User Data/*/History",
            "chromium": local_appdata / "Chromium/User Data/*/History",
            "firefox":  appdata_roaming / "Mozilla/Firefox/Profiles/*/places.sqlite",
            "librewolf": appdata_roaming / "LibreWolf/Profiles/*/places.sqlite",
        }
    elif system == "Darwin":  # macOS
        library = home / "Library/Application Support"
        return {
            "chrome":   library / "Google/Chrome/*/History",
            "edge":     library / "Microsoft Edge/*/History",
            "brave":    library / "BraveSoftware/Brave-Browser/*/History",
            "chromium": library / "Chromium/*/History",
            "firefox":  library / "Firefox/Profiles/*/places.sqlite",
            "librewolf": library / "librewolf/Profiles/*/places.sqlite",
        }
    elif system == "Linux":
        config = home / ".config"
        mozilla = home / ".mozilla"
        return {
            "chrome":   config / "google-chrome/*/History",
            "edge":     config / "microsoft-edge/*/History",
            "brave":    config / "BraveSoftware/Brave-Browser/*/History",
            "chromium": config / "chromium/*/History",
            "firefox":  mozilla / "firefox/*/places.sqlite",
            "librewolf": home / ".librewolf/*/places.sqlite",
        }
    else:
        raise NotImplementedError(f"Unsupported OS: {system}")

BROWSER_PROFILE_GLOBS = get_browser_profile_globs()

  
# 2. Low-level helpers
  
from contextlib import contextmanager

@contextmanager
def copy_db_locked(original: pathlib.Path) -> pathlib.Path:
    """Copy locked SQLite file to temp location with auto-cleanup."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        shutil.copy2(original, tmp.name)
        yield pathlib.Path(tmp.name)
    pathlib.Path(tmp.name).unlink(missing_ok=True)

def _chrome_datetime(microseconds_since_epoch: int) -> datetime:
    """Convert Chrome's 1601-01-01 epoch to datetime."""
    return datetime(1601, 1, 1, tzinfo=timezone.utc) + \
           timedelta(microseconds=microseconds_since_epoch)

def _firefox_datetime(micro_seconds_since_epoch: int) -> datetime:
    """Convert Firefox's Unix epoch to datetime."""
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + \
           timedelta(microseconds=micro_seconds_since_epoch)

  
# 3. Readers per browser
  
def _read_chrome_like(history_file: pathlib.Path) -> List[Tuple[str, str, datetime]]:
    """
    Read history from Chrome-like browsers (Chrome, Edge, Brave, Chromium).
    Returns: [(url, title, last_visit_time), ...]
    Limits to 10000 newest entries.
    """
    with copy_db_locked(history_file) as tmp:
        conn = sqlite3.connect(tmp)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT url, title, last_visit_time FROM urls "
            "WHERE url IS NOT NULL AND title IS NOT NULL "
            "ORDER BY last_visit_time DESC LIMIT 10000"
        )
        rows = [
            (row["url"], row["title"] or "",
             _chrome_datetime(row["last_visit_time"]))
            for row in cur.fetchall()
        ]
        conn.close()
    return rows

def _read_firefox_like(places_file: pathlib.Path) -> List[Tuple[str, str, datetime]]:
    """
    Read history from Firefox-like browsers (Firefox, LibreWolf).
    Returns: [(url, title, visit_date), ...]
    Limits to 10000 newest entries.
    """
    with copy_db_locked(places_file) as tmp:
        conn = sqlite3.connect(tmp)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT moz_places.url, moz_places.title, moz_historyvisits.visit_date "
            "FROM moz_places "
            "JOIN moz_historyvisits ON moz_places.id = moz_historyvisits.place_id "
            "WHERE moz_places.url IS NOT NULL "
            "ORDER BY moz_historyvisits.visit_date DESC LIMIT 10000"
        )
        rows = [
            (row["url"], row["title"] or "",
             _firefox_datetime(row["visit_date"]))
            for row in cur.fetchall()
        ]
        conn.close()
    return rows

  
# 4. Discover installed browsers & load everything
  
def load_all_history() -> List[Tuple[str, str, str, datetime]]:
    """
    Load history from all supported browsers.
    Returns: [(browser_name, url, title, when), ...]
    Sorted by date descending, deduplicated by URL (case-insensitive).
    """
    combined: List[Tuple[str, str, str, datetime]] = []
    for browser, pattern in BROWSER_PROFILE_GLOBS.items():
        for db_path in glob.glob(str(pattern)):
            db_path = pathlib.Path(db_path)
            if not db_path.exists():
                continue
            try:
                if browser in {"firefox", "librewolf"}:
                    rows = _read_firefox_like(db_path)
                else:
                    rows = _read_chrome_like(db_path)
                combined.extend((browser, url, title, when) for url, title, when in rows)
            except (sqlite3.DatabaseError, PermissionError, shutil.Error) as e:
                print(f"[WARN] Skipped {browser} history at {db_path}: {e}", file=sys.stderr)
    # Deduplicate, keeping newest visit
    seen = {}
    for browser, url, title, when in combined:
        key = url.lower()
        if key not in seen or when > seen[key][3]:
            seen[key] = (browser, url, title, when)
    return sorted(seen.values(), key=lambda t: t[3], reverse=True)

  
# 5. GUI Application
  
class HistorySearchGUI:
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("Browser History Search")
        self.master.geometry("800x600")
        
        self.all_entries: List[Tuple[str, str, str, datetime]] = []
        self.filtered_entries: List[Tuple[str, str, str, datetime]] = []
        
        self.create_widgets()
        self.load_history()
    
    def create_widgets(self):
        """Create GUI widgets for search, filtering, and display."""
        # Search frame
        search_frame = ttk.Frame(self.master)
        search_frame.pack(pady=10, padx=10, fill="x")
        
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_results)
        
        # Browser filter
        ttk.Label(search_frame, text="Browser:").pack(side="left", padx=5)
        self.browser_var = tk.StringVar()
        self.browser_combo = ttk.Combobox(search_frame, textvariable=self.browser_var, 
                                        values=["All"] + list(BROWSER_PROFILE_GLOBS.keys()))
        self.browser_combo.current(0)
        self.browser_combo.pack(side="left", padx=5)
        self.browser_combo.bind("<<ComboboxSelected>>", self.filter_results)
        
        # Date range
        date_frame = ttk.Frame(self.master)
        date_frame.pack(pady=5, padx=10, fill="x")
        
        ttk.Label(date_frame, text="From Date (YYYY-MM-DD):").pack(side="left", padx=5)
        self.from_date_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.from_date_var, width=12).pack(side="left", padx=5)
        
        ttk.Label(date_frame, text="To Date (YYYY-MM-DD):").pack(side="left", padx=5)
        self.to_date_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.to_date_var, width=12).pack(side="left", padx=5)
        
        ttk.Button(date_frame, text="Apply Date Filter", command=self.filter_results).pack(side="left", padx=5)
        
        # Results treeview
        self.tree = ttk.Treeview(self.master, columns=("Browser", "Date", "Title", "URL"), show="headings")
        self.tree.heading("Browser", text="Browser")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Title", text="Title")
        self.tree.heading("URL", text="URL")
        self.tree.column("Browser", width=100)
        self.tree.column("Date", width=150)
        self.tree.column("Title", width=200)
        self.tree.column("URL", width=300)
        self.tree.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Bind double-click to open URL
        self.tree.bind("<Double-1>", self.open_url)
        
        # Export buttons
        export_frame = ttk.Frame(self.master)
        export_frame.pack(pady=10, padx=10, fill="x")
        
        ttk.Button(export_frame, text="Export to JSON", command=self.export_to_json).pack(side="left", padx=5)
        ttk.Button(export_frame, text="Export to CSV", command=self.export_to_csv).pack(side="left", padx=5)
    
    def load_history(self):
        """Load and display all browser history."""
        try:
            self.all_entries = load_all_history()
            self.filtered_entries = self.all_entries[:] 
            self.update_tree()
            messagebox.showinfo("Loaded", f"Loaded {len(self.all_entries)} history entries.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load history: {e}")
    
    def filter_results(self, event=None):
        """Filter history based on search query, browser, and date range."""
        query = self.search_var.get().lower()
        browser_filter = self.browser_var.get() if self.browser_var.get() != "All" else None
        from_date = self.parse_date(self.from_date_var.get())
        to_date = self.parse_date(self.to_date_var.get(), is_to=True)
        
        self.filtered_entries = [
            (b, u, t, d) for b, u, t, d in self.all_entries
            if (not query or query in u.lower() or query in t.lower())
            and (not browser_filter or b == browser_filter)
            and (not from_date or d >= from_date)
            and (not to_date or d <= to_date)
        ]
        self.update_tree()
    
    def parse_date(self, date_str: str, is_to: bool = False) -> Optional[datetime]:
        """Parse date string (YYYY-MM-DD) to datetime."""
        if not date_str:
            return None
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            if is_to:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
            return None
    
    def update_tree(self):
        """Update Treeview with filtered results."""
        self.tree.delete(*self.tree.get_children())
        for b, u, t, d in self.filtered_entries:
            self.tree.insert("", END, values=(b, d.strftime("%Y-%m-%d %H:%M"), t or "-", u))
    
    def open_url(self, event):
        """Open selected URL in default browser on double-click."""
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        url = item["values"][3]  # URL is in the 4th column
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open URL: {e}")
    
    def export_to_json(self):
        """Export filtered results to JSON file."""
        if not self.filtered_entries:
            messagebox.showinfo("No Data", "No results to export.")
            return
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if file:
            try:
                with open(file, "w", encoding="utf-8") as f:
                    json.dump(
                        [{"browser": b, "url": u, "title": t, "date": d.isoformat()} 
                         for b, u, t, d in self.filtered_entries],
                        f, indent=2
                    )
                messagebox.showinfo("Exported", f"Exported to {file}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export JSON: {e}")
    
    def export_to_csv(self):
        """Export filtered results to CSV file."""
        if not self.filtered_entries:
            messagebox.showinfo("No Data", "No results to export.")
            return
        file = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if file:
            try:
                with open(file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Browser", "Date", "Title", "URL"])
                    for b, u, t, d in self.filtered_entries:
                        writer.writerow([b, d.strftime("%Y-%m-%d %H:%M"), t or "-", u])
                messagebox.showinfo("Exported", f"Exported to {file}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export CSV: {e}")

  
# 6. CLI entry point
  
if __name__ == "__main__":
    root = tk.Tk()
    app = HistorySearchGUI(root)
    root.mainloop()