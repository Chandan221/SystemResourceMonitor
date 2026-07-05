import psutil
import os
import time
from pathlib import Path


def get_cpu_stats():
    per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
    overall = sum(per_cpu) / len(per_cpu) if per_cpu else 0
    return overall, per_cpu


def get_cpu_usage():
    return get_cpu_stats()[0]


def get_cpu_freq():
    freq = psutil.cpu_freq()
    if freq:
        return freq.current
    return 0


def get_cpu_count():
    return psutil.cpu_count(logical=True)


def get_ram_usage():
    mem = psutil.virtual_memory()
    return mem.percent, mem.used, mem.total


def get_disk_partitions():
    partitions = []
    for p in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(p.mountpoint)
            partitions.append({
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            })
        except PermissionError:
            continue
    return partitions


def get_disk_usage(path="/"):
    usage = psutil.disk_usage(path)
    return {
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "percent": usage.percent,
    }


def format_bytes(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def get_folder_size(path, follow_symlinks=False):
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=follow_symlinks):
                        total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=follow_symlinks):
                        total += get_folder_size(entry.path, follow_symlinks)
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    return total


def get_subfolder_sizes(path, max_items=20):
    items = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        size = get_folder_size(entry.path)
                        items.append((entry.name, size, entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        size = entry.stat().st_size
                        items.append((entry.name, size, entry.path))
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:max_items]


def get_network_io():
    net = psutil.net_io_counters()
    return net.bytes_sent, net.bytes_recv


def get_process_count():
    return len(psutil.pids())


def get_per_cpu_usage():
    return get_cpu_stats()[1]


def get_top_processes(limit=10, sort_by="cpu"):
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if sort_by == "cpu":
        processes.sort(key=lambda p: p['cpu_percent'] or 0, reverse=True)
    else:
        processes.sort(key=lambda p: p['memory_percent'] or 0, reverse=True)
    return processes[:limit]


def get_battery_info():
    try:
        bat = psutil.sensors_battery()
        if bat:
            return {
                "percent": bat.percent,
                "charging": bat.power_plugged,
                "time_left": bat.secsleft if bat.secsleft != -1 else None,
            }
    except AttributeError:
        pass
    return None


def _guess_interface_type(name):
    n = name.lower().replace(" ", "").replace("-", "").replace("_", "")
    if any(k in n for k in ["loopback", "lo"]):
        return "Loopback"
    if any(k in n for k in ["vmware", "vmnet", "vbox", "virtual"]):
        return "Virtual"
    if any(k in n for k in ["docker", "veth", "bridge"]):
        return "Virtual"
    if any(k in n for k in ["wifi", "wireless", "wlan"]):
        return "WiFi"
    if any(k in n for k in ["ethernet", "eth", "gbe", "pcie"]):
        return "Ethernet"
    if any(k in n for k in ["bluetooth", "bt"]):
        return "Bluetooth"
    if any(k in n for k in ["ppp", "pppoe", "wan"]):
        return "WAN"
    return "Unknown"


def get_network_interfaces():
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    interfaces = []
    for name, stat in stats.items():
        ip = ""
        for a in addrs.get(name, []):
            if a.family == 2:
                ip = a.address
                break
        interfaces.append({
            "name": name,
            "isup": stat.isup,
            "speed": stat.speed,
            "ip": ip,
            "type": _guess_interface_type(name),
        })
    return interfaces


_net_prev = None
_net_prev_time = None


def get_network_speed():
    global _net_prev, _net_prev_time
    current = psutil.net_io_counters()
    now = time.time()
    sent_speed = 0
    recv_speed = 0
    if _net_prev is not None and _net_prev_time is not None:
        dt = now - _net_prev_time
        if dt > 0:
            sent_speed = (current.bytes_sent - _net_prev.bytes_sent) / dt
            recv_speed = (current.bytes_recv - _net_prev.bytes_recv) / dt
    _net_prev = current
    _net_prev_time = now
    return sent_speed, recv_speed, current.bytes_sent, current.bytes_recv


def format_speed(bps):
    if bps < 1024:
        return f"{bps:.1f} B/s"
    elif bps < 1024 * 1024:
        return f"{bps / 1024:.1f} KB/s"
    elif bps < 1024 * 1024 * 1024:
        return f"{bps / (1024 * 1024):.1f} MB/s"
    return f"{bps / (1024 * 1024 * 1024):.1f} GB/s"


SPEED_UNITS = ["B/s", "KB/s", "MB/s", "Kbps", "Mbps"]


def format_speed_custom(bps, unit):
    if unit == "B/s":
        return f"{bps:.1f} B/s"
    elif unit == "KB/s":
        return f"{bps / 1024:.1f} KB/s"
    elif unit == "MB/s":
        return f"{bps / (1024 * 1024):.1f} MB/s"
    elif unit == "Kbps":
        return f"{(bps * 8) / 1000:.1f} Kbps"
    elif unit == "Mbps":
        return f"{(bps * 8) / (1000 * 1000):.1f} Mbps"
    return format_speed(bps)


FILE_TYPE_CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico", ".webp", ".tiff", ".raw"},
    "Documents": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".odt", ".csv", ".md"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "Video": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Archives": {".zip", ".rar", ".tar", ".gz", ".7z", ".bz2", ".xz", ".iso"},
    "Code": {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h", ".hpp",
             ".cs", ".rb", ".php", ".go", ".rs", ".swift", ".kt", ".scala", ".pl",
             ".sh", ".bat", ".ps1", ".sql", ".html", ".css", ".scss", ".less", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg"},
    "Executables": {".exe", ".msi", ".dll", ".so", ".dylib", ".bin", ".app", ".jar"},
    "Fonts": {".ttf", ".otf", ".woff", ".woff2", ".eot"},
    "Others": set(),
}


def categorize_extension(ext):
    ext = ext.lower()
    for category, extensions in FILE_TYPE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "Others"


def scan_files_by_type(root_path, progress_callback=None):
    files_by_ext = {}
    total_found = 0
    try:
        for dirpath, _, filenames in os.walk(root_path):
            for fname in filenames:
                try:
                    fpath = os.path.join(dirpath, fname)
                    size = os.path.getsize(fpath)
                    ext = os.path.splitext(fname)[1].lower() or "(no extension)"
                    if ext not in files_by_ext:
                        files_by_ext[ext] = {"files": [], "total_size": 0, "count": 0}
                    files_by_ext[ext]["files"].append({
                        "name": fname,
                        "path": fpath,
                        "size": size,
                    })
                    files_by_ext[ext]["total_size"] += size
                    files_by_ext[ext]["count"] += 1
                    total_found += 1
                    if progress_callback and total_found % 100 == 0:
                        progress_callback(total_found)
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass

    groups = {}
    for ext, data in files_by_ext.items():
        category = categorize_extension(ext)
        if category not in groups:
            groups[category] = {"extensions": {}, "total_size": 0, "total_count": 0}
        groups[category]["extensions"][ext] = data
        groups[category]["total_size"] += data["total_size"]
        groups[category]["total_count"] += data["count"]

    for cat_data in groups.values():
        cat_data["extensions"] = dict(
            sorted(cat_data["extensions"].items(),
                   key=lambda x: x[1]["total_size"], reverse=True)
        )

    groups = dict(
        sorted(groups.items(),
               key=lambda x: x[1]["total_size"], reverse=True)
    )
    return groups, total_found


def delete_file(file_path):
    try:
        os.remove(file_path)
        return True, None
    except Exception as e:
        return False, str(e)
