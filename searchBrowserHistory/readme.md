Browser History Search
A cross-platform Python tool with a graphical user interface (GUI) to search and manage browser history from multiple browsers, including Chrome, Edge, Brave, Chromium, Firefox, and LibreWolf. It supports Windows, Linux, and macOS, with features like keyword search, browser and date filtering, and exporting results to JSON or CSV.
Features

Cross-Platform Support: Works on Windows, Linux, and macOS.
Multiple Browsers: Supports Chrome, Edge, Brave, Chromium, Firefox, and LibreWolf.
GUI Interface: Search history with a user-friendly Tkinter-based interface.
Advanced Filtering: Filter by keyword, browser, or date range.
Export Options: Save results to JSON or CSV files.
Deduplication: Removes duplicate URLs, keeping the most recent visit.
Performance: Limits history retrieval to 10,000 entries per browser for efficiency.

Requirements

Python 3.6 or higher
Tkinter (usually included with Python; may need manual installation on some Linux systems)
No additional Python packages required (uses standard library)

Installation Instructions
1. Install Python
Ensure Python 3.6+ is installed on your system. Download it from python.org or use a package manager.
Windows

Download and install Python from python.org.
Ensure the option to add Python to your PATH is checked during installation.
Verify installation by running:python --version



Linux

Most Linux distributions include Python. Install it if needed:# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-tk

# Fedora
sudo dnf install python3 python3-tkinter


Verify installation:python3 --version



macOS

Python is often pre-installed, or you can install it via Homebrew:brew install python


Verify installation:python3 --version



2. Download the Script

Save the script as search_my_history.py in a directory of your choice.
Alternatively, clone or download the repository if available:git clone <repository-url>
cd <repository-directory>



3. Verify Tkinter
Tkinter is required for the GUI. It’s included with Python on Windows and macOS. On Linux, ensure python3-tk (or equivalent) is installed (see Linux installation above).
Test Tkinter:
python3 -m tkinter

A small test window should appear. If not, install Tkinter as shown above.
4. Run the Application
Navigate to the directory containing search_my_history.py and run:
python3 search_my_history.py

The GUI window will open, displaying browser history and allowing you to search and filter.
Usage

Launch the GUI: Run the script as described above.
Search History:
Enter keywords in the search bar (case-insensitive).
Select a browser from the dropdown to filter results (default: All).
Optionally, enter a date range (YYYY-MM-DD) in the "From Date" and "To Date" fields.
Click "Apply Date Filter" or press Enter in the search bar to update results.


View Results: Results appear in a table with columns for Browser, Date, Title, and URL.
Export Results:
Click "Export to JSON" or "Export to CSV" to save the filtered results.
Choose a file location and name in the dialog that appears.



Notes

Browser Support: The tool reads history from default profile locations. Custom profile paths are not supported.
Permissions: Ensure you have read access to browser history files (e.g., ~/Library/Application Support/ on macOS, ~/.config/ on Linux, or %LocalAppData% on Windows).
Performance: The tool limits history to 10,000 entries per browser to avoid memory issues.
Locked Files: The script copies locked SQLite databases to temporary files to avoid conflicts with running browsers.

Troubleshooting

No history loaded:
Ensure browsers are installed and have history files in default locations.
Check for permission errors in the console output.


Tkinter not found:
Install python3-tk (Linux) or reinstall Python with Tkinter support.


Invalid date format:
Use YYYY-MM-DD format (e.g., 2025-10-10) for date filters.



License
This project is licensed under the MIT License.