# Isolated Unreal collaboration

## Current decision — 2026-09-23

The owner approved a **headless Linux game-server VM with separate NetBird**,
independent developer checkouts, GitHub login and shared runtime GM. Follow
[development-environment.md](development-environment.md) for implementation status.
This supersedes the full Editor VM as the current delivery target. The design
below is retained as deferred research; its license/GPU blockers do not prevent
a headless server design. They must not be represented as solved. Host work
Tailscale stays strictly off limits; all remote admission remains closed.

## Deferred full Editor VM design

**Access is closed.** The Windows VM has not been provisioned: the owner has no
guest license or installation ISO. Native content sharing rights, guest graphics,
firewall isolation and two-machine acceptance are also outstanding.

## Linux guest feasibility

Linux removes the Windows guest-license requirement and supports Unreal Editor
and Multi-User collaboration. Epic recommends Ubuntu 22.04 for UE 5.8 and requires
Vulkan-capable graphics. A server-only Linux VM does not require an Editor GPU,
but leaving the owner's Editor on the personal host would not satisfy this
project's isolation requirement. The full Editor VM remains blocked by graphics:
Microsoft does not support Hyper-V GPU-P or DDA on Windows desktop hosts, and the
owner's Radeon RX 7700 XT is not on Microsoft's supported GPU-P list. Buying a
Windows guest license would not resolve that hardware/host support limitation.
Do not deploy a server-only VM and describe the complete design as achieved.
A dedicated project machine or a supported GPU-virtualization host would require
a separately approved deployment decision; do not replace the host OS or weaken
isolation as a workaround.

Sources: [Epic Linux requirements](https://dev.epicgames.com/documentation/unreal-engine/linux-development-requirements-for-unreal-engine),
[Epic Multi-User overview](https://dev.epicgames.com/documentation/en-us/unreal-engine/multi-user-editing-overview-for-unreal-engine),
[Microsoft GPU support limits](https://learn.microsoft.com/en-us/troubleshoot/windows-server/virtualization/troubleshoot-hyper-v-gpu-assignment-partitioning-passthrough-issues).

## Host firewall change

On 2026-09-22, eight broad local inbound Allow rules for Unreal Editor,
UnrealEditor-Cmd, UnrealPak and UnrealTraceServer were backed up, disabled and
verified in the effective Windows Firewall policy. They had allowed any remote
address on Private/Public profiles. `close-host-unreal-firewall.ps1` previews
matching rules by default; `-Apply` requires Windows administrator elevation.
Exact rule IDs and original state are saved privately in
`artifacts/collaboration/host-unreal-firewall-before-*.json`. For a deliberate
rollback, review that file and use `Enable-NetFirewallRule -PolicyStore
PersistentStore -Name <exact-saved-name>` for only the intended rules. No work VPN
settings were queried or changed. This targeted change is not proof that every
host service is isolated; guest/network acceptance remains mandatory.

## Account boundary

The existing host Tailscale installation belongs to work. Using that account for
this project is forbidden. Do not inspect its credentials, log it out, switch its
account, change its ACLs/routes, or reuse its identity. The owner supplied a
different project account, recorded only in ignored local setup notes. Install
and authenticate the project VPN **inside the guest only**. Collaborators use
their own computers; grant no host/guest Windows accounts, desktop, shell, SMB,
WinRM, subnet-router or exit-node access.

The Multi-User service and the owner's collaborative Editor run as a standard
guest user. The personal host must not open a collaborative session. Project
plugins, scripts and assets can execute code: review changes before loading them,
and keep all personal credentials and production database secrets outside the VM.

## Provisioning and security gates

1. Run `scripts/unreal/collaboration-audit.ps1` for a private, read-only host report.
   It deliberately never calls Tailscale. Verify updates, Defender, firewall,
   encryption/recovery and remote-service exposure. Missing permissions are
   recorded as unavailable, never as a pass.
2. Obtain a valid Windows guest license and ISO; no purchase is authorized by this
   implementation. In an administrator maintenance session, enable Hyper-V if
   needed and use `create-collaboration-vm.ps1 -IsoPath ... -GuestLicenseEvidence ...`.
   It creates an offline, Secure Boot/TPM VM with a dynamic 160 GiB disk, 4 vCPUs,
   and 8–16 GiB RAM. It does not restart Windows, start the VM or attach networking.
3. Name the guest `AEGIS-UNREAL`. Create a standard local project user and a separate
   local administrator for maintenance. Disable guest RDP, SSH, WinRM, file/print
   sharing, drive/clipboard/device redirection and credential forwarding. Use
   basic VM console access only; disable enhanced-session services in the guest.
   Leave host VM settings for unrelated workloads unchanged.
4. Validate actual Unreal 5.8.2 Editor rendering/performance in the VM. CPU and RAM
   availability are not evidence of usable virtual graphics. Do not fall back to
   running collaboration in the personal host session if this fails.
5. Configure a dedicated virtual network with an enforced egress boundary. No
   host or physical-LAN access is permitted. Use deny-by-default guest firewall
   rules and a host/hypervisor enforcement layer that blocks private/LAN and host
   destinations even if the guest is compromised. Permit only documented VPN,
   update and project-source endpoints. Validate DNS, IPv4 and IPv6 separately.
   Do not attach the VM to the default/external switch as an unchecked shortcut.
6. Sign in to the **separate project** Tailscale account inside the guest. Enable
   MFA in its identity provider, approve only named collaborators/devices, disable
   file transfer, SSH, routing and exit nodes, and replace default allow-all rules.
   `project-vpn-policy.example.json` is a starting template for the new project
   account only; substitute its owner, collaborator identities and server address.
   Validate the policy in that account's policy editor before applying it.
7. Permit approved peer addresses to the guest's Unreal UDP 50000 endpoint only.
   Document/test the actual UDP reply flow; do not broadly permit all VPN traffic.
   Keep management ports and unrelated guest services blocked. Record rules and
   rollback before changes. No host-work VPN modifications are allowed.

## Content and session workflow

The private repository is `briantheLEDguy/War-js-content`. It initially contains
an inventory and closed distribution manifest, not a ready-to-install asset pack.
`migration/native-content-policy.json` has no distribution approvals. Review
repository model provenance, owner-supplied animations/artwork and each purchased
kit before approving content roots with a concrete evidence document. Review
collaborator entitlement separately. Never upload unreviewed purchased packages.

`npm run unreal:content-inventory` hashes current native packages; only approved
roots are copied into ignored `artifacts/native-content-repo`. Commit/push that
private checkout after review, then pin its commit and manifest SHA-256 in
`migration/native-content.lock.json`. Both repositories use Git LFS where needed.
`unreal:content-check -- <checkout>` and `unreal:content-sync -- <checkout>` reject
incomplete distribution, wrong revisions/hashes and conflicting local edits.
They never delete local content. The source manifest records the code revision
used to capture it; the code-side lock selects the compatible content revision.

Fetch full code history and the browser reference tag for historical acceptance
evidence. Build native code, install matching content, and compare manifests on
every participating machine before joining. Session persistence changes project
assets; designate one integrator to persist, review and commit them to the private
repository. Coordinate code changes through Git/rebuilds between sessions.
Keep runtime GM drafts separately backed up; they are not the Multi-User session
archive and are not automatically promoted to authored maps.

The guest helper supports `Preflight`, `Server`, and `Editor`. It rejects the host
before discovering Tailscale, requires the supplied project owner to match the
guest VPN identity, and rejects administrator execution. Editor launch enables
MultiUserClient only for that process. The public project does not activate
collaboration on the personal host by default.

## Acceptance, revocation and recovery

Keep `collaboratorAccess` closed until the deployment is actually tested. For the
controlled acceptance session, an administrator must manually start the isolated
server under the standard account with only the designated test peers admitted;
the normal launcher cannot certify itself. Record machine identity, code/content
commits, firewall/VPN policy revisions, tester, time and concrete evidence for each
`requiredEvidence` entry. Only after all pass may the policy become `verified`.

From a collaborator device, verify editing succeeds but host/LAN connectivity,
RDP, SMB, SSH, WinRM, unrelated services and unrelated repositories fail. Verify
the guest cannot access host files/credentials or initiate host/LAN connections.
Test IPv6 and alternate NICs, reconnect, server restart, persisted asset recovery
and immediate revocation. Then confirm a clean checkout reproduces the result.
No remote acceptance has been performed yet.

For normal sessions, pass the recorded evidence to the guest launcher. Revoke
access by removing the collaborator's project VPN grant/device and repository
access, then terminate their existing session and verify reconnection fails.
Shut down the named server process at session end; retain private session archives
and Git/LFS revisions. Take encrypted off-device backups and test restoration;
same-disk recovery snapshots do not cover disk loss. Never publish session archives
or purchased content into the public repository.
