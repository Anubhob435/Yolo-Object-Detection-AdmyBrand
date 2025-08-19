import psutil
import platform
import GPUtil
import json

def get_system_info():
    """Get comprehensive system information as a structured dictionary."""
    system_info = {}
    
    # System Information
    uname = platform.uname()
    system_info['system'] = {
        'system': uname.system,
        'node_name': uname.node,
        'release': uname.release,
        'version': uname.version,
        'machine': uname.machine,
        'processor': uname.processor
    }

    # CPU Information
    cpufreq = psutil.cpu_freq()
    system_info['cpu'] = {
        'physical_cores': psutil.cpu_count(logical=False),
        'total_cores': psutil.cpu_count(logical=True),
        'max_frequency': round(cpufreq.max, 2) if cpufreq else 0,
        'min_frequency': round(cpufreq.min, 2) if cpufreq else 0,
        'current_frequency': round(cpufreq.current, 2) if cpufreq else 0,
        'cpu_usage': psutil.cpu_percent(interval=1)
    }

    # Memory Information
    svmem = psutil.virtual_memory()
    system_info['memory'] = {
        'total_gb': round(svmem.total / (1024**3), 2),
        'available_gb': round(svmem.available / (1024**3), 2),
        'used_gb': round(svmem.used / (1024**3), 2),
        'percentage': svmem.percent
    }

    # Disk Information
    system_info['disks'] = []
    partitions = psutil.disk_partitions()
    for partition in partitions:
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
            disk_info = {
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'filesystem': partition.fstype,
                'total_gb': round(partition_usage.total / (1024**3), 2),
                'used_gb': round(partition_usage.used / (1024**3), 2),
                'free_gb': round(partition_usage.free / (1024**3), 2),
                'percentage': round(partition_usage.percent, 1)
            }
            system_info['disks'].append(disk_info)
        except PermissionError:
            continue

    # GPU Information
    system_info['gpus'] = []
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            for i, gpu in enumerate(gpus):
                gpu_info = {
                    'id': i,
                    'name': gpu.name,
                    'driver': gpu.driver,
                    'total_memory_mb': gpu.memoryTotal,
                    'used_memory_mb': gpu.memoryUsed,
                    'free_memory_mb': gpu.memoryFree,
                    'load_percent': round(gpu.load * 100, 2),
                    'temperature_c': round(gpu.temperature, 2)
                }
                system_info['gpus'].append(gpu_info)
        else:
            system_info['gpu_note'] = "No NVIDIA GPUs found or GPUtil is not configured correctly."
    except Exception as e:
        system_info['gpu_error'] = str(e)
    
    return system_info

def print_system_info():
    """Print system information in a formatted way (for CLI usage)."""
    info = get_system_info()
    
    print("="*40, "System Information", "="*40)
    for key, value in info['system'].items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    print("="*40, "CPU Information", "="*40)
    cpu = info['cpu']
    print(f"Physical cores: {cpu['physical_cores']}")
    print(f"Total cores: {cpu['total_cores']}")
    print(f"Max Frequency: {cpu['max_frequency']:.2f}Mhz")
    print(f"Min Frequency: {cpu['min_frequency']:.2f}Mhz")
    print(f"Current Frequency: {cpu['current_frequency']:.2f}Mhz")
    print(f"Total CPU Usage: {cpu['cpu_usage']}%")

    print("="*40, "Memory Information", "="*40)
    mem = info['memory']
    print(f"Total: {mem['total_gb']} GB")
    print(f"Available: {mem['available_gb']} GB")
    print(f"Used: {mem['used_gb']} GB")
    print(f"Percentage: {mem['percentage']}%")

    print("="*40, "Disk Information", "="*40)
    for disk in info['disks']:
        print(f"--- Device: {disk['device']} ---")
        print(f"  Mountpoint: {disk['mountpoint']}")
        print(f"  File system type: {disk['filesystem']}")
        print(f"  Total Size: {disk['total_gb']} GB")
        print(f"  Used: {disk['used_gb']} GB")
        print(f"  Free: {disk['free_gb']} GB")
        print(f"  Percentage: {disk['percentage']}%")

    print("="*40, "GPU Information", "="*40)
    if info['gpus']:
        for gpu in info['gpus']:
            print(f"--- GPU {gpu['id']} ---")
            print(f"  Name: {gpu['name']}")
            print(f"  Driver: {gpu['driver']}")
            print(f"  Total Memory: {gpu['total_memory_mb']}MB")
            print(f"  Used Memory: {gpu['used_memory_mb']}MB")
            print(f"  Free Memory: {gpu['free_memory_mb']}MB")
            print(f"  GPU Load: {gpu['load_percent']}%")
            print(f"  Temperature: {gpu['temperature_c']}C")
    elif 'gpu_note' in info:
        print(info['gpu_note'])
    elif 'gpu_error' in info:
        print(f"Error getting GPU information: {info['gpu_error']}")

if __name__ == "__main__":
    print_system_info()