"""
capture_environment.py: Automated Environment and Reproducibility Manifest Generator.

Captures system specifications, compiler versions, library dependencies,
git provenance, and configuration state while strictly excluding usernames,
home paths, credentials, and private identifiers.
"""

import datetime
import json
import os
import platform
import subprocess

import zstandard


def get_command_output(cmd_args):
    try:
        res = subprocess.run(cmd_args, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:  # noqa: BLE001
        return "Not available"


def get_git_info():
    commit = get_command_output(["git", "rev-parse", "HEAD"])
    branch = get_command_output(["git", "branch", "--show-current"])
    git_version = get_command_output(["git", "--version"])
    return {
        "commit": commit,
        "branch": branch,
        "git_version": git_version,
    }


def get_forge_info():
    forge_path = r"C:\Users\user\.foundry\bin\forge.exe"
    if os.path.exists(forge_path):
        out = get_command_output([forge_path, "--version"])
    else:
        out = get_command_output(["forge", "--version"])
    return out


def get_node_info():
    node_v = get_command_output(["node", "--version"])
    npm_v = get_command_output(["npm", "--version"])
    return {"node_version": node_v, "npm_version": npm_v}


def get_system_specs():
    specs = {
        "os_name": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "machine_architecture": platform.machine(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
    }
    # On Windows, query total physical memory without exposing user paths
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            specs["total_physical_memory_bytes"] = stat.ullTotalPhys
            specs["total_physical_memory_gib"] = round(stat.ullTotalPhys / (1024**3), 2)
    except Exception:  # noqa: BLE001
        specs["total_physical_memory_gib"] = "Unknown"

    return specs


def get_python_packages():
    try:
        import importlib.metadata

        packages = {}
        for dist in sorted(
            importlib.metadata.distributions(), key=lambda d: d.metadata["Name"].lower()
        ):
            name = dist.metadata["Name"]
            packages[name] = dist.version
        return packages
    except Exception:  # noqa: BLE001
        return {}


def capture_environment(
    output_path="benchmarks/journal-extension/manifests/environment.json",
    cache_state="warm",
    random_seed=42,
):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    env_record = {
        "timestamp_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "experiment_configuration": {
            "random_seed": random_seed,
            "cache_state": cache_state,
            "evm_target": "cancun",
            "blob_schedule": "EIP-4844 Cancun baseline (3 target, 6 max)",
            "solidity_compiler_version": "0.8.24",
            "solidity_optimizer_runs": 200,
        },
        "git_provenance": get_git_info(),
        "system_hardware": get_system_specs(),
        "toolchain": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "zstandard_library_version": zstandard.__version__,
            "foundry_forge": get_forge_info(),
            "node_runtime": get_node_info(),
        },
        "python_dependencies": get_python_packages(),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(env_record, f, indent=2)

    print(f"[OK] Environment manifest written to {output_path}")
    return env_record


if __name__ == "__main__":
    capture_environment()
