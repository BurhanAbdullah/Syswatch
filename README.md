# SYSWATCH PRO

SYSWATCH PRO is a lightweight host security monitoring and intrusion detection framework written in Bash.  
It provides system monitoring, threat detection, and security auditing capabilities for Linux systems and container environments.

The project focuses on building a modular and extensible monitoring tool that can inspect system activity, detect suspicious behavior, and provide insight into potential security risks.

SYSWATCH PRO is designed to run in development environments, servers, containers, and cloud instances.

---

## Overview

SYSWATCH PRO performs continuous monitoring of system resources and security indicators.  
It analyzes processes, network activity, file integrity, and system configuration to identify anomalies and potential threats.

The tool operates using modular scripts that can be extended to support additional monitoring and detection capabilities.

---

## Key Capabilities

### System Monitoring
- CPU, memory, and disk utilization tracking
- Top resource consuming processes
- Network port inspection
- Active connection monitoring

### Security Monitoring
- Suspicious process detection
- Reverse shell pattern detection
- Crypto-miner indicator detection
- Malware pattern scanning

### Network Analysis
- Listening port inspection
- External connection monitoring
- Detection of unusual network activity

### System Hardening Inspection
- SUID binary detection
- Cron job persistence inspection
- Startup file monitoring
- Firewall configuration checks

### File Integrity Monitoring
- Baseline hash database generation
- Detection of modified system files
- Integrity verification scans

### Environment Awareness
- Container environment detection
- Kernel and operating system inspection
- Host identification

### Threat Assessment
- Threat scoring system
- Risk classification
- Security alert reporting

---

## Architecture

SYSWATCH PRO follows a modular design.  
Each module performs a specific inspection or monitoring task.
