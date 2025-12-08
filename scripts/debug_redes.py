import subprocess

def debug_netsh_scan():
    proc = subprocess.run(
        "netsh wlan show networks mode=bssid",
        shell=True,
        capture_output=True,
        text=True,         # decodifica a str
        encoding="cp850",  # consola español/latino normalmente
        errors="ignore",
    )
    print("=== STDOUT ===")
    print(proc.stdout)
    print("=== STDERR ===")
    print(proc.stderr)
    print("=== RETURN CODE:", proc.returncode)

if __name__ == "__main__":
    debug_netsh_scan()