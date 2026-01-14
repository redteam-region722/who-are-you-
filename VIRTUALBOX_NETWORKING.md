# VirtualBox Networking Guide

## Problem: Client on Windows Can't Connect to Server on Ubuntu VirtualBox

When running the server in Ubuntu VirtualBox and client on Windows host, connection fails due to VirtualBox networking configuration.

## Solution Options

### Option 1: Port Forwarding (Easiest - Recommended)

**Best for:** Quick testing, NAT mode

**Steps:**

1. **Find your Ubuntu VM's IP:**
   ```bash
   # Inside Ubuntu VM
   hostname -I
   # Example output: 10.0.2.15
   ```

2. **Configure VirtualBox Port Forwarding:**
   - Open VirtualBox Manager
   - Select your Ubuntu VM
   - Click **Settings** → **Network**
   - Select **Adapter 1** (should be NAT)
   - Click **Advanced** → **Port Forwarding**
   - Click **+** (Add new rule)
   - Configure:
     - **Name:** `remote-desktop`
     - **Protocol:** `TCP`
     - **Host IP:** (leave empty or `127.0.0.1`)
     - **Host Port:** `8443`
     - **Guest IP:** (leave empty)
     - **Guest Port:** `8443`
   - Click **OK**

3. **Start Server on Ubuntu VM:**
   ```bash
   python3 server/server.py --host 0.0.0.0 --port 8443
   ```

4. **Connect Client from Windows:**
   ```cmd
   python client\client.py --server-host 127.0.0.1 --server-port 8443
   ```
   **Note:** Use `127.0.0.1` (localhost) because port forwarding makes it appear as localhost!

### Option 2: Bridged Networking (Best for Production)

**Best for:** Making VM accessible as a real network device

**Steps:**

1. **Change VirtualBox Network Mode:**
   - Open VirtualBox Manager
   - Select your Ubuntu VM
   - Click **Settings** → **Network**
   - Select **Adapter 1**
   - Change **Attached to:** from `NAT` to **`Bridged Adapter`**
   - Select your network adapter (e.g., `Intel(R) Wi-Fi 6 AX200...`)
   - Click **OK**

2. **Restart Ubuntu VM**

3. **Find Ubuntu VM's IP Address:**
   ```bash
   # Inside Ubuntu VM
   hostname -I
   # Example output: 192.168.1.105
   ```

4. **Start Server on Ubuntu VM:**
   ```bash
   python3 server/server.py --host 0.0.0.0 --port 8443
   ```

5. **Connect Client from Windows:**
   ```cmd
   # Use the IP address from step 3
   python client\client.py --server-host 192.168.1.105 --server-port 8443
   ```

### Option 3: Host-Only Networking (Isolated Network)

**Best for:** VM-to-Host communication only (no internet in VM)

**Steps:**

1. **Create Host-Only Adapter (if needed):**
   - VirtualBox Manager → **File** → **Host Network Manager**
   - Click **Create**
   - Note the IP range (e.g., `192.168.56.1`)

2. **Configure VM Network:**
   - Select Ubuntu VM → **Settings** → **Network**
   - **Adapter 1:** Keep as NAT (for internet)
   - **Adapter 2:** Enable
     - **Attached to:** `Host-only Adapter`
     - Select the adapter created above
   - Click **OK**

3. **Restart Ubuntu VM**

4. **Find Ubuntu VM's Host-Only IP:**
   ```bash
   # Inside Ubuntu VM
   ip addr show
   # Look for adapter with 192.168.56.x address
   # Example: 192.168.56.101
   ```

5. **Start Server on Ubuntu VM:**
   ```bash
   python3 server/server.py --host 0.0.0.0 --port 8443
   ```

6. **Connect Client from Windows:**
   ```cmd
   # Use the Host-Only IP from step 4
   python client\client.py --server-host 192.168.56.101 --server-port 8443
   ```

## Troubleshooting

### Connection Refused / Can't Connect

**Check 1: Server is running and binding correctly**
```bash
# On Ubuntu VM
python3 server/server.py --host 0.0.0.0 --port 8443
# Should see: "Server listening on 0.0.0.0:8443"
```

**Check 2: Verify IP address**
```bash
# On Ubuntu VM
hostname -I
# Use this IP for client connection (if bridged/host-only)
# Or use 127.0.0.1 (if port forwarding)
```

**Check 3: Test connectivity from Windows**
```cmd
# On Windows host
ping 192.168.1.105  # Replace with your VM's IP
# Or if using port forwarding:
telnet 127.0.0.1 8443
```

**Check 4: Check firewall**
```bash
# On Ubuntu VM
sudo ufw status
# Allow port 8443 if needed:
sudo ufw allow 8443/tcp
```

### Firewall Issues

**Ubuntu Firewall (UFW):**
```bash
sudo ufw allow 8443/tcp
sudo ufw status
```

**Windows Firewall:**
- Windows Security → Firewall → Allow an app
- Ensure Python is allowed

### Wrong IP Address

**Common mistake:** Using VM's internal IP when using NAT mode
- **NAT mode:** Use port forwarding + `127.0.0.1` on client
- **Bridged mode:** Use VM's bridged IP (same network as host)
- **Host-only mode:** Use VM's host-only IP

## Quick Reference

### Port Forwarding Setup
1. VM Settings → Network → Port Forwarding
2. Add rule: TCP, Host Port 8443, Guest Port 8443
3. Server: `python3 server/server.py --host 0.0.0.0 --port 8443`
4. Client: `python client\client.py --server-host 127.0.0.1 --server-port 8443`

### Bridged Networking Setup
1. VM Settings → Network → Bridged Adapter
2. Restart VM
3. Find VM IP: `hostname -I` (in VM)
4. Server: `python3 server/server.py --host 0.0.0.0 --port 8443`
5. Client: `python client\client.py --server-host <VM_IP> --server-port 8443`

## Network Mode Comparison

| Mode | Pros | Cons | Use Case |
|------|------|------|----------|
| **NAT + Port Forwarding** | Easy setup, VM has internet | Port forwarding needed | Testing, development |
| **Bridged** | VM appears as real device, easy access | Requires network access | Production-like setup |
| **Host-Only** | Isolated, secure | No internet in VM | Secure testing |

## Recommended Setup

**For testing:** Use **Port Forwarding** (Option 1) - easiest and works immediately

**For production-like:** Use **Bridged Networking** (Option 2) - VM acts like real machine

## Verification Steps

1. ✅ Server shows: "Server listening on 0.0.0.0:8443"
2. ✅ VM IP is correct (check with `hostname -I`)
3. ✅ Port forwarding configured (if using NAT)
4. ✅ Firewall allows port 8443
5. ✅ Client uses correct IP address
6. ✅ Network mode configured correctly
