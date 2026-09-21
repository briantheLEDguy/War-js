# Native character progression

Fresh characters retain the browser defaults: level 1, zero XP/gold, 100 max
health, 100 max mana and 10 base strength. The next level requires
`100 + 150 * current level` XP. Each level adds 20 max health, 10 max mana and
2 base strength, consumes its threshold and restores health/mana. A single
reward can gain multiple levels. Equipment strength is added separately, so
unequipping does not remove earned base stat growth.

`GrantCharacterRewards` is a trusted C++ server API, not a client RPC. It commits
XP, gold, bag items, deferred items and the inventory revision together under
one transaction ID. Invalid items, negative rewards, overflow, repeated IDs and
session receipt limits reject without changing progression. Full bags retain
campaign-style deferred gear without replaying XP/gold when that gear is later
delivered. Quest turn-in still needs its separate strict capacity/quest checks.

Progression shares the owner-only inventory snapshot. GAS receives grown maximum
pools on level-up and pawn initialization, preserving stats across respawn.
Restoring pools does not clear the pawn's death state. Client equip/use/craft/
salvage/cultivation/gather requests require a living, visually ready pawn.
The inventory panel shows level, current/required XP, gold and effective strength.

`npm run unreal:progression-fixtures` executes the actual browser `checkLevelUp`
inside Vitest and captures nine boundary/multilevel cases. The fixture includes
a source fingerprint; ordinary tooling tests compare the fixture to the browser
without rewriting it. Native automation consumes the same cases and adds
negative/overflow, duplicate reward, full-bag and equipment strength checks.

This remains session-local. Durable settlement, real enemy/quest/campaign reward
triggers, ability unlock notifications/grants, complete stat-scaled combat and
public target/nameplate presentation remain unfinished. The development strike
still deals its fixed proof damage; displaying strength does not claim that
all ability damage formulas are ported. The pure rule accepts normalized states
and nonnegative 32-bit reward deltas; XP/gold totals use 64-bit integers and
stat growth fails explicitly before overflow.

Verified on 2026-09-21: 15 native Foundation automation groups and 74 migration
tooling tests passed; tools typechecking and the Windows Development package
build passed. Rendered two-client proofs passed in editor mode
(`artifacts/unreal/network/1789975335488-7600/report.json`) and with packaged
Windows clients (`artifacts/unreal/network/1789975760063-32804/report.json`).
The sequence levels both owners to 3, rejects repeated rewards, verifies private
progression, kills the defender through GAS damage, and verifies the replacement
pawn retains its inventory and 140/120 maximum pools. These are local-loopback
development tests, not production persistence or three-platform acceptance.
