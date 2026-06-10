# System Resource Monitor

A modern Windows desktop application for monitoring system resources in real-time. Built with Python, CustomTkinter, psutil, and matplotlib.

[![Download v1.0.4](https://img.shields.io/badge/Download-v1.0.4-00e676?style=for-the-badge&logo=windows)](https://github.com/Chandan221/SystemResourceMonitor/releases/download/v1.0.4/SystemResourceMonitor.exe)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?logo=windows)
![Version](https://img.shields.io/badge/Version-v1.0.4-blue)

---

## Features

- **Dashboard** — real-time circular gauges for CPU, RAM, and disk usage; stat cards for frequency, cores, processes, uptime, and battery; line charts for CPU/memory history; per-core CPU breakdown (horizontally scrollable) with individual utilization percentages; top processes sorted by CPU usage
- **Network Monitor** — real-time upload/download speed gauges with configurable speed units (Auto, B/s, KB/s, MB/s, Kbps, Mbps), speed history chart, and per-interface details with connection type detection (WiFi, Ethernet, Bluetooth, Virtual)
- **Disk Usage** — per-partition breakdown with progress bars showing used, free, and total space across all mounted drives
- **Folder Analyzer** — select any directory and scan its contents to get a sorted, size-based breakdown of subfolders and files
- **File Analyzer** — deep-scan any directory to group all files by category (Images, Documents, Audio, Video, Code, etc.) with per-extension breakdowns and individual file sizes; delete unwanted files directly from the app
- **Dark/Light Theme Toggle** — switch between dark and light appearance modes from the sidebar
- **Configurable Refresh Interval** — adjust the monitoring refresh rate from 1s to 10s via a sidebar slider
- **Export to CSV** — save CPU and memory usage history to a CSV file for external analysis

---

## Download

### v1.0.4 — Standalone Executable

[⬇ Download SystemResourceMonitor.exe](https://github.com/Chandan221/SystemResourceMonitor/releases/download/v1.0.4/SystemResourceMonitor.exe) (35 MB, no dependencies required)

Just download and run — works on Windows 10 and 11.

---

## Run from Source

```bash
pip install -r requirements.txt
python main.py
```

## Usage

1. Launch the application
2. Use the sidebar to navigate between Dashboard, Disk Usage, Folder Analyzer, File Analyzer, and Network Monitor
3. Dashboard updates automatically every 2 seconds (configurable via sidebar slider)
4. In Folder Analyzer, click "Select Folder" to choose a directory, then "Scan Sizes"
5. In Network Monitor, select your preferred speed unit from the dropdown

## Build from Source

```bash
pip install pyinstaller
pyinstaller SystemResourceMonitor.spec
```

The executable will be placed in the `dist/` directory.

## Requirements

- Python 3.9+
- Windows 10/11
- Dependencies listed in `requirements.txt`

---

## Support

If you find this project useful, consider supporting its development:

### Ko-fi
<a href='https://ko-fi.com/I6V0210BSB' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi2.png?v=3' border='0' alt='Support me on Ko-fi' /></a>

### UPI (Indian Users)
```
paytmqr5h4w8I@ptys
```

---

## License

MIT
