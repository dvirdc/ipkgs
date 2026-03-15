# ipkgs

**The package manager for Verilog IP cores.**

`ipkgs` is to Verilog what `npm` is to JavaScript — a CLI tool and registry for sharing, installing, and publishing reusable RTL IP cores for FPGA and ASIC projects.

Registry: **[ipkgs.com](https://ipkgs.com)**

---

## Install

```sh
pip install ipkgs
```

## Quick start

```sh
# Initialize a new IP core project
ipkgs init

# Search for IP cores
ipkgs search uart

# Install a package
ipkgs install uart-core

# Install a specific version
ipkgs install fifo-sync@^2.0.0

# List installed packages
ipkgs list

# Publish your core to ipkgs.com
ipkgs login
ipkgs publish
```

## `ipkgs.json`

Every IP core project has an `ipkgs.json` manifest:

```json
{
  "name": "uart-core",
  "version": "1.2.0",
  "description": "Parameterized UART TX/RX for FPGA targets",
  "author": "Your Name <you@example.com>",
  "license": "MIT",
  "top_module": "uart_top",
  "platforms": ["ice40", "ecp5", "xc7", "generic"],
  "source_files": [
    "rtl/uart_top.sv",
    "rtl/uart_tx.sv",
    "rtl/uart_rx.sv"
  ],
  "parameters": {
    "BAUD_RATE": "115200",
    "DATA_BITS": "8"
  },
  "dependencies": {
    "fifo-sync": "^2.0.0"
  },
  "scripts": {
    "sim":  "iverilog -g2012 -o sim.out rtl/uart_top.sv && vvp sim.out",
    "lint": "verilator --lint-only rtl/uart_top.sv"
  }
}
```

Installed packages land in `ip_modules/` (add to `.gitignore`).

## Commands

| Command | Description |
|---|---|
| `ipkgs init` | Scaffold a new IP core project |
| `ipkgs install [pkg[@ver]]` | Install packages |
| `ipkgs uninstall <pkg>` | Remove packages |
| `ipkgs update [pkg]` | Update to latest within semver range |
| `ipkgs list` | List installed packages |
| `ipkgs search <query>` | Search the registry |
| `ipkgs info <pkg>` | Show package details |
| `ipkgs publish` | Publish to ipkgs.com |
| `ipkgs login` | Authenticate with ipkgs.com |
| `ipkgs logout` | Remove stored credentials |

## Version ranges

`ipkgs` uses standard semver ranges:

| Range | Meaning |
|---|---|
| `^1.2.0` | Compatible: `>=1.2.0 <2.0.0` |
| `~1.2.0` | Patch-level: `>=1.2.0 <1.3.0` |
| `>=1.0.0 <2.0.0` | Explicit range |
| `1.2.3` | Exact version |

> **Note on version conflicts:** Unlike npm, `ipkgs` hard-fails on incompatible version conflicts. Verilog IP cores compile into a single netlist — duplicate module definitions would cause synthesis errors. If two packages require incompatible versions of a dependency, you must resolve the conflict manually.

## Environment variables

| Variable | Description |
|---|---|
| `IPKGS_TOKEN` | Auth token (for CI/CD, skips keyring) |
| `IPKGS_REGISTRY` | Override registry URL (default: `https://api.ipkgs.com/v1`) |

## License

MIT
