# Development setup checkpoint - 2026-09-23

Paused at the owner's request to return to game editing. These observations
come from user-supplied screenshots and console output, not an isolation audit.
Remote admission and production gates remain closed.

## Exact resume point

NetBird CLI 0.79.0 is installed inside the Ubuntu guest and its service started.
`netbird up` has NOT been run in this walkthrough. The next requested action
has NOT been confirmed complete:

1. Open https://app.netbird.io in the Windows browser and establish the separate
   AegisWar development account. Do not modify an existing work organization.
2. Inspect Access Control / Policies and disable the new account's default
   all-peers/all-protocols policy before enrolling the guest or inviting users.
3. Configure restricted project groups/policies and required control/relay
   egress. Package-server access alone is insufficient for enrollment.
4. Verify overlay firewall behavior, forwarding, host/LAN isolation and actual
   two-machine tests before collaborator admission. Do not assume UFW alone
   governs overlay traffic after NetBird installation.

Account creation, policies, enrollment and invitations remain unverified.
Do not install a host VPN as an implicit next step. The host work Tailscale
installation/account is forbidden to read, modify, switch or reuse.

## VM and networking evidence

- Hyper-V VM `AegisWar-DevServer`: Generation 2, four vCPUs, 8 GiB RAM,
  80 GB virtual disk; guest root filesystem approximately 76 GB.
- Ubuntu Server 22.04.5 LTS, hostname `aegis-dev-server`, owner login `loc`.
- Adapter `Network Adapter` connected to internal switch `AegisWar-Dev-Isolated`.
  Default Switch was not modified.
- Gateway `172.30.240.1/29`, Preferred; NAT `AegisWar-Dev-NAT`,
  prefix `172.30.240.0/29`.
- Guest eth0 `172.30.240.2/29`, default route via `172.30.240.1`, DNS `1.1.1.1`.
- Netplan `/etc/netplan/50-cloud-init.yaml`, mode 600, networkd, DHCP and IPv6
  RA disabled, link-local empty, optional true. Cloud-init network-disable
  instructions were given; verify that file exists on resumption.
- MAC spoofing off; DHCP guard and router guard on.
- IPv4 and IPv6 forwarding both reported zero. Before NetBird installation,
  listening sockets showed only systemd-resolved on `127.0.0.53:53`.
- After upgrade/reboot: no failed systemd units, IP and UFW settings persisted.
- Console keyboard stopped responding once despite healthy heartbeat.
  Graceful Stop-VM followed by Start-VM restored input.

## Firewall configuration

UFW active at startup, default deny incoming/outgoing, routed disabled.
Outbound eth0 allowances match these destinations. No incoming game, API,
SSH, desktop or file-sharing allowances were added.

Hyper-V extended ACLs retain inbound and outbound ANY deny rules at weight 1.
All allowances are outbound, stateful, bound to local IP `172.30.240.2`:

| Destination | Protocol/port | Weight | Idle timeout |
|---|---|---|---|
| 1.1.1.1 | UDP 53 | 100 | 60 s |
| 1.1.1.1 | TCP 53 | 101 | 60 s |
| 185.125.190.81, 185.125.190.82, 185.125.190.83 | TCP 80 | 200-202 | 300 s |
| 91.189.91.81, 91.189.91.82, 91.189.91.83 | TCP 80 | 203-205 | 300 s |
| 91.189.92.22, 91.189.92.23, 91.189.92.24 | TCP 80 | 206-208 | 300 s |
| 5.22.212.152 | TCP 443 | 300 | 300 s |
| 194.113.73.12 | TCP 443 | 301 | 300 s |

The first 13 ACLs were directly shown. The last two host commands were supplied
and successful downloads followed, but a full 15-rule listing is still needed.
NetBird package DNS changed during setup and initially caused a timeout.
Fixed-IP rules need maintenance; do not replace them with unrestricted egress.
Actual host/LAN isolation, controlled bypass tests and two-machine proof remain
outstanding. Configuration checks alone do not certify isolation.

## Packages

- Ubuntu sources: HTTP archive.ubuntu.com and security.ubuntu.com, Jammy main,
  restricted, universe, multiverse, updates, backports and security.
- APT update and upgrade completed, then reboot succeeded. Last package command
  reported **8 not upgraded**. Inspect holds, phasing and dependencies before
  claiming all updates complete.
- ca-certificates, curl and gnupg installed.
- Downloaded NetBird key over HTTPS from pkgs.netbird.io/debian/public.key to
  `~/netbird-key.asc`. Observed fingerprint:
  `EFE3 7DF0 47DF 7CCD F1FC 54FA 83F7 9AD0 2977 8355`, UID Wiretrustee.
  This is not independent out-of-band fingerprint verification.
- Keyring `/usr/share/keyrings/netbird-archive-keyring.gpg`; repository file
  `/etc/apt/sources.list.d/netbird.list`, using repository-scoped signed-by.
- NetBird repository refresh and CLI installation succeeded; `netbird version`
  returned `0.79.0`. No UI package installed.

## Remaining project work

See [implementation record](development-environment.md) and
[long-term strategy](architecture/mmo-hosting-2026-09-23.md).
Actual GitHub OAuth login and owner bootstrap remain unverified. Native saves,
normal authenticated joins, active revocation, shared GM synchronization,
source-built Linux dedicated server, deployment, content distribution rights,
and two-machine combat/recovery acceptance remain outstanding.

Branch `codex/free-development-multiplayer` contains uncommitted implementation
work. Preserve it when editing the game. This checkpoint does not commit,
deploy or certify that implementation. No game runtime files changed here.
