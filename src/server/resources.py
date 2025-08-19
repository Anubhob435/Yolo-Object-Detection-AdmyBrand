import psutil
import platform
import GPUtil

def get_system_info():
    print("="*40, "System Information", "="*40)
    uname = platform.uname()
    print(f"System: {uname.system}")
    print(f"Node Name: {uname.node}")
    print(f"Release: {uname.release}")
    print(f"Version: {uname.version}")
    print(f"Machine: {uname.machine}")
    print(f"Processor: {uname.processor}")

    print("="*40, "CPU Information", "="*40)
    print(f"Physical cores: {psutil.cpu_count(logical=False)}")
    print(f"Total cores: {psutil.cpu_count(logical=True)}")
    cpufreq = psutil.cpu_freq()
    print(f"Max Frequency: {cpufreq.max:.2f}Mhz")
    print(f"Min Frequency: {cpufreq.min:.2f}Mhz")
    print(f"Current Frequency: {cpufreq.current:.2f}Mhz")
    print(f"Total CPU Usage: {psutil.cpu_percent(interval=1)}%")

    print("="*40, "Memory Information", "="*40)
    svmem = psutil.virtual_memory()
    print(f"Total: {svmem.total / (1024**3):.2f} GB")
    print(f"Available: {svmem.available / (1024**3):.2f} GB")
    print(f"Used: {svmem.used / (1024**3):.2f} GB")
    print(f"Percentage: {svmem.percent}%")

    print("="*40, "Disk Information", "="*40)
    partitions = psutil.disk_partitions()
    for partition in partitions:
        print(f"--- Device: {partition.device} ---")
        print(f"  Mountpoint: {partition.mountpoint}")
        print(f"  File system type: {partition.fstype}")
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
            print(f"  Total Size: {partition_usage.total / (1024**3):.2f} GB")
            print(f"  Used: {partition_usage.used / (1024**3):.2f} GB")
            print(f"  Free: {partition_usage.free / (1024**3):.2f} GB")
            print(f"  Percentage: {partition_usage.percent}%")
        except PermissionError:
            continue

    print("="*40, "GPU Information", "="*40)
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            for i, gpu in enumerate(gpus):
                print(f"--- GPU {i} ---")
                print(f"  Name: {gpu.name}")
                print(f"  Driver: {gpu.driver}")
                print(f"  Total Memory: {gpu.memoryTotal}MB")
                print(f"  Used Memory: {gpu.memoryUsed}MB")
                print(f"  Free Memory: {gpu.memoryFree}MB")
                print(f"  GPU Load: {gpu.load*100:.2f}%")
                print(f"  Temperature: {gpu.temperature:.2f}C")
        else:
            print("No NVIDIA GPUs found or GPUtil is not configured correctly.")
    except Exception as e:
        print(f"Error getting GPU information: {e}")

get_system_info()