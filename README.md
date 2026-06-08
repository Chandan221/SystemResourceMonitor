# System Resource Monitor

A modern Windows desktop application for monitoring system resources in real-time. Built with Python, CustomTkinter, psutil, and matplotlib.

[![Download v1.0.0](https://img.shields.io/badge/Download-v1.0.0-00e676?style=for-the-badge&logo=windows)](https://github.com/Chandan221/SystemResourceMonitor/releases/download/v1.0.0/SystemResourceMonitor.exe)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?logo=windows)

---

## Features

- **Dashboard** — real-time circular gauges for CPU, RAM, and disk usage; stat cards for frequency, cores, processes, and uptime; live line charts tracking CPU and memory history (60-second window)
- **Disk Usage** — per-partition breakdown with progress bars showing used, free, and total space across all mounted drives
- **Folder Analyzer** — select any directory and scan its contents to get a sorted, size-based breakdown of subfolders and files

---

## Download

### v1.0.0 — Standalone Executable

[⬇ Download SystemResourceMonitor.exe](https://github.com/Chandan221/SystemResourceMonitor/releases/download/v1.0.0/SystemResourceMonitor.exe) (34 MB, no dependencies required)

Just download and run — works on Windows 10 and 11.

---

## Run from Source

```bash
pip install -r requirements.txt
python main.py
```

## Usage

1. Launch the application
2. Use the sidebar to navigate between Dashboard, Disk Usage, and Folder Analyzer
3. Dashboard updates automatically every 2 seconds
4. In Folder Analyzer, click "Select Folder" to choose a directory, then "Scan Sizes"

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

## License

MIT
