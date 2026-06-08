import psutil
import os
from pathlib import Path


def get_cpu_usage():
    return psutil.cpu_percent(interval=0.1)


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
