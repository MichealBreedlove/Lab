# Cisco Nexus 3064 — Config Backup

## Export Running Config

```
ssh admin@<switch-ip>
show running-config
```

Copy output to: `Lab/network/switches/cisco_nexus_3064/running-config.txt`

## Automated Export (if SSH available)

```bash
ssh admin@<ip> "show running-config" > running-config.txt
```

## Notes
- Redact any passwords/community strings before committing
- Export after any config changes
