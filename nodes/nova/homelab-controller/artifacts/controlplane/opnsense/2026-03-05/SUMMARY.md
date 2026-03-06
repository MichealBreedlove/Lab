# OPNsense Inventory -- 2026-03-06T00:26:40Z
Host: 10.1.1.1
HTTPS reachable: yes
SSH enabled: no (port 22 closed)
API credentials: NOT configured
Config backup: yes

## Setup Instructions
To enable API-based backup:
1. OPNsense UI > System > Access > Users > [user] > Create API Key
2. Save key+secret REDACTED ~/.config/homelab/secrets.env:
   OPNSENSE_API_KEY=your_key
   OPNSENSE_API_SECRET=your_secret
REDACTED3. Re-run: oc controlplane full

To enable SSH (optional):
1. OPNsense UI > System > Settings > Administration
2. Enable Secure Shell, set port (22 or custom)
3. Update inventory/group_vars/opnsense.yml with port
