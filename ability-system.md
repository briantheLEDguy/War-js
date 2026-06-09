# Dark Fantasy Class Ability System Blueprint

## Current-state read of your uploaded pipeline

I inspected your uploaded zip locally. The bundle is primarily a **Blender and MCP-based character/content export pipeline**, not a gameplay ability framework. In practical terms, it already has the right *content-side* ingredients for class presentation—career-specific character generation, modular equipment exports, slot metadata, and a small shared animation library—but it does **not** appear to include the dedicated gameplay-side layer you need for cooldowns, resources, target logic, status effects, interrupts, cancel rules, hit confirmation, or loadout composition.

That distinction matters. The strongest modern ability architectures treat **abilities, attributes, effects, and tags** as first-class gameplay data, while animation, collision checks, and VFX are attached to those gameplay objects as tasks or events. Epic’s Gameplay Ability System is explicit about that separation: it is built around attributes, abilities, interactions, tags, costs, cooldowns, and reusable tasks, rather than embedding combat logic inside content-export tooling. citeturn19view0turn19view1turn19view2

My main conclusion from the upload is therefore straightforward: **keep Blender responsible for meshes, rigs, weights, sockets, attachment metadata, and animation clips; move combat logic into a data-driven runtime ability layer.** That is the cleanest path to better combat feel, cleaner iteration, and much higher art quality because it stops the exporter from carrying gameplay responsibilities it was never designed to own. citeturn19view0turn19view1turn19view2

## Research-backed design pillars for your ability system

A good system for your game should be built on five pillars.

The first pillar is a **data-driven ability object model**. A mature pattern is to define each ability through a reusable schema that stores activation conditions, costs, targeting, effects, cooldowns, and tags. Epic’s documentation frames this as a system of owned abilities, attributes, effects, and hierarchical tags that can block, cancel, or permit execution in a consistent way. That is especially useful for a class-heavy RPG because it lets you express “stealthed,” “casting,” “needs shield,” “melee finisher,” “burning target,” or “can interrupt” as standardized gameplay tags instead of ad hoc code branches. citeturn19view0turn19view1turn19view2

The second pillar is **reliable hit logic**. Epic’s ARPG sample distinguishes melee abilities from skill abilities by using weapon overlaps for melee and skill-specific trace logic for targeted abilities. That distinction is exactly what your project needs. Do not use raw rendered mesh collision for combat. Use authored melee windows, traces, and collision shapes attached to ability events. This produces cleaner combat, fewer “I obviously hit that” failures, and much easier balancing. citeturn19view3turn19view4

The third pillar is **animation-aware combat timing**. Animation Notifies and Notify Windows are useful because they let you define exact active frames, release frames, and root-motion control windows. Layered animation is equally important because it lets a character move and act at the same time—for example, running while aiming or strafing while casting—without requiring a unique full-body clip for every state combination. Your current pipeline will feel dramatically better if attacks are authored as “wind-up → active window → recovery” and if ranged or hybrid classes can play upper-body attack layers over locomotion. citeturn19view5turn19view6

The fourth pillar is **modular character construction on a single rig contract**. Epic’s modular character documentation, Unreal’s Mutable release notes, Khronos glTF skinning guidance, and the Three.js `SkinnedMesh` docs all point in the same direction: interchangeable character parts work best when they share a consistent skeleton contract, correct skin weights, and stable bind relationships. Three.js also notes that skinned meshes require valid skin indices and weights, and that `DetachedBindMode` is useful when sharing a skeleton across multiple skinned meshes. Mutable specifically calls out hidden surface removal to prevent z-fighting and mesh/texture merging to reduce draw calls. In short: if you want configurable armor that still deforms and animates cleanly, every equippable piece has to obey one skeleton, one pose contract, and one masking policy. citeturn21view1turn21view3turn21view0turn21view2turn19view10

The fifth pillar is **combat readability over material noise**. Riot’s VALORANT rendering write-up is from a different genre, but the principle is universal: depth, silhouette, and visibility must beat raw detail, especially at distance. If you push “realistic” armor too far without readability discipline, you get muddy silhouettes and unreadable combat. For your dark fantasy game, realism should live in materials, wear, and surface breakup—not in cluttered silhouettes that hide weapons, hand poses, impact direction, or class identity. citeturn20view0

Taken together, those findings suggest a very clear target architecture for your project:

| System layer | What it should own |
|---|---|
| **Class design layer** | class identity, resource mechanic, role, counterplay windows |
| **Ability data layer** | cooldown, cost, tags, target type, effects, interrupt rules |
| **Animation layer** | clip selection, notify windows, blend rules, additive overlays |
| **Combat runtime layer** | traces, overlaps, hit confirmation, status application, AI usage |
| **Character art layer** | body, armor, weapon meshes, sockets, skinning, materials, masks |
| **VFX/SFX layer** | socket-based spawn points, timing hooks, impact readability |

## Renamed class roster

For IP purposes, the safest framing is: **mechanics and broad archetypes are usually not protected by copyright, but specific names, titles, distinctive expressions, and branding can create copyright or trademark risk depending on how closely they track the source expression and whether similar marks are already in use.** The U.S. Copyright Office states that game ideas, methods of play, names, and titles are not protected by copyright as such, while the USPTO stresses that trademark conflicts turn on confusing similarity and that clearance searching is an essential step. So the mapping below is a **creative-distancing plan**, not legal clearance. You should still run final names through a trademark clearance search before shipping. citeturn19view12turn19view13turn19view14turn19view15turn18search6

| Old name | Proposed new name | Why this is directionally safer |
|---|---|---|
| Bright Wizard | **Ember Arcanist** | Keeps the fire-mage fantasy, drops the exact iconic phrase |
| Witch Hunter | **Hex Inquisitor** | Preserves zealot-investigator feel without the canonical title |
| Knight of the Blazing Sun | **Sunfire Templar** | Retains radiant martial identity, removes distinctive wording |
| Warrior Priest | **Battle Prelate** | Keeps frontline holy-warrior meaning, changes expression |
| Ironbreaker | **Stoneguard** | Keeps defensive dwarf-tank feel, avoids the specific compound |
| Slayer | **Doomseeker** | Preserves grim berserker fantasy with different language |
| Rune Priest | **Glyphbinder** | Keeps rune-magic support identity without the exact title |
| Engineer | **Siegewright** | Conveys blackpowder/mechanical warfare in a distinct way |
| Swordmaster | **Blade Savant** | Keeps disciplined sword-form fantasy, not the original title |
| White Lion | **Pride Warden** | Keeps beast-hunter/lion-partner feel with new phrasing |
| Archmage | **Aether Sage** | Maintains elite mage fantasy with a more generic expression |
| Shadow Warrior | **Veil Ranger** | Keeps stealth archer identity, avoids the exact phrase |
| Chosen | **Dreadsworn** | Retains dark anointed champion feel with different wording |
| Marauder | **Warped Reaver** | Keeps mutation-raider fantasy, avoids the exact title |
| Magus | **Void Magister** | Preserves occult artillery caster fantasy with new wording |
| Zealot | **Ruin Oracle** | Keeps dark ritualist/support feel without the exact label |
| Black Orc | **Warbrute** | Keeps armored greenskin bruiser fantasy, changes title fully |
| Squig Herder | **Fang Herder** | Preserves goblin beast-handler role, removes the famous noun |
| Shaman | **Bog Hexer** | Keeps swampy goblin spellcaster identity with more specificity |
| Choppa | **Cleaver** | Preserves aggressive melee bruiser identity with generic wording |
| Witch Elf | **Blood Dancer** | Keeps assassin-priestess vibe without the exact title |
| Blackguard | **Dread Guard** | Maintains dark bodyguard fantasy with less distinctive wording |
| Sorceress | **Dusk Weaver** | Preserves dark female caster feel but changes expression |
| Disciple of Khaine | **Crimson Acolyte** | Keeps blood-rite melee-healer identity, removes deity reference |

## Order class plans

The class-fantasy grounding below is based on current Return of Reckoning career references. Empire careers are described there as a high-risk fire caster, an accusation-and-execution hybrid, a battlefield-command tank, and a melee-centered support/healer powered by righteous fury. Dwarf careers emphasize grudge-fueled reaction, escalating rage, rune-based support, and mechanical contraptions. High Elf careers emphasize chained sword forms, beast partnership, offensive/defensive magical balance, and mobile stance-based archery. citeturn14search3turn23search15turn5search3turn23search12turn6search0turn6search1turn7search0turn7search1turn7search2turn10search1turn8search0turn10search0

**Empire**

| Class | Intended playstyle | Ten-ability kit |
|---|---|---|
| **Ember Arcanist**<br>old: Bright Wizard | High-risk ranged glass cannon. Builds **Heat** for bigger crits and bigger self-burn risk. Strong lane control, DoTs, and climactic spenders. | **1. Spark Lash** — quick fire bolt; builds Heat.<br>**2. Cinder Lance** — heavier single-target nuke; bonus crit at high Heat.<br>**3. Kindle Hex** — DoT that causes the next fire hit to splash.<br>**4. Soot Veil** — smoke cone; reduces enemy accuracy and breaks target lock feel.<br>**5. Flashstep** — short blink leaving a burning trail.<br>**6. Pyre Circle** — ground AoE ring for zone denial.<br>**7. White Cautery** — risky cauterize heal on self or ally; small heal plus purge, minor self-burn.<br>**8. Furnace Heart** — self-buff; Heat gain doubles, backlash risk rises.<br>**9. Ashen Cataclysm** — channeled beam that consumes Heat for burst damage.<br>**10. Phoenix Collapse** — ultimate meteor strike; empties Heat and scorches a large area. |
| **Hex Inquisitor**<br>old: Witch Hunter | Mobile hybrid duelist/assassin. Builds **Verdicts** with pistol and blade, then spends them on executions. Best when flanking or isolating casters. | **1. Brand Shot** — pistol shot; applies 1 Verdict.<br>**2. Interrogate** — rapier stab; weakens armor and adds 1 Verdict.<br>**3. Silver Snare** — thrown chain/net root.<br>**4. Relic Oil** — weapon anoint; bonus damage versus marked targets.<br>**5. Purging Slash** — fast melee combo; spends Verdicts for burst.<br>**6. Black-Powder Step** — evasive sidestep/backstep with a return shot.<br>**7. Stake the Guilty** — execute; stronger from rear or against low-health enemies.<br>**8. Ash Ward** — self-cleanse and brief anti-magic ward.<br>**9. Torch of Scorn** — cone burn that panics weak enemies.<br>**10. Final Sentence** — ultimate execution shot; enormous single-target damage if cast at full Verdict. |
| **Sunfire Templar**<br>old: Knight of the Blazing Sun | Aura commander tank. Rotates **Edicts** and brands targets for allied follow-up. Defensive enough for front line; active enough to stay fun. | **1. Solar Edict** — toggle aura for ally offense.<br>**2. Bastion Edict** — toggle aura for ally defense.<br>**3. Pursuit Edict** — toggle aura for speed and AP tempo.<br>**4. Sunbrand Strike** — melee hit that marks a target for team procs.<br>**5. Shield of Noon** — frontal block stance against ranged pressure.<br>**6. Rallying Rebuke** — taunt plus enemy damage reduction.<br>**7. Banner Rush** — shield-led engage/charge.<br>**8. Radiant Counter** — riposte after block or parry; briefly blinds.<br>**9. Heavenrend Sweep** — wide cleave that spends built-up Valor from ally combat nearby.<br>**10. Daybreak Standard** — ultimate banner zone granting CC resistance, morale gain, and steady healing pulses. |
| **Battle Prelate**<br>old: Warrior Priest | Frontline melee-healer. Builds **Zeal** by attacking and spends it on blessings, burst healing, and hammer impacts. | **1. Litany of Strikes** — hammer combo; builds Zeal.<br>**2. Sanctified Blow** — empowered hit that heals nearby allies.<br>**3. Martyr’s Ward** — targeted shield for self or ally.<br>**4. Penance Step** — short gap-close with a slow.<br>**5. Hymn of Resolve** — chant aura; allies heal slightly when striking.<br>**6. Reliquary Smash** — overhead AoE stagger.<br>**7. Judgment of Ash** — line-based holy shock at mid range.<br>**8. Redemption Surge** — spend Zeal for group burst heal.<br>**9. Icon of Wrath** — place relic that grants melee lifesteal in an area.<br>**10. Last Homily** — ultimate sermon; for a short window, damage dealt by the Prelate is echoed as ally healing. |

**Dwarf**

| Class | Intended playstyle | Ten-ability kit |
|---|---|---|
| **Stoneguard**<br>old: Ironbreaker | Reactive protector tank. Builds **Grudge** from being hit or seeing an **Oathmate** attacked, then cashes it out into punishing responses. | **1. Oath Bind** — designate ally; share protection and gain Grudge when either is pressured.<br>**2. Grudge Axes** — ranged axe toss taunt.<br>**3. Clanwall** — shield slam with short stagger.<br>**4. Bitter Reprisal** — high-damage retaliatory strike; scales with Grudge.<br>**5. Runebound Mail** — heavy armor buff, stronger near Oathmate.<br>**6. Stone March** — slow unstoppable advance.<br>**7. Holdfast** — planted defensive stance; huge block, limited movement.<br>**8. Vengeful Hook** — chain-pull to punish overextended targets.<br>**9. Hearthguard Vow** — cleanse and shield transfer to Oathmate.<br>**10. Book of Wrongs** — ultimate; consume full Grudge to create a taunt field with retaliatory shockwaves. |
| **Doomseeker**<br>old: Slayer | Hyper-aggressive berserker. Builds **Rage** for damage, but becomes easier to kill if greed wins over judgment. | **1. Death Oath** — enter berserk state; Rage decay slows, defense drops.<br>**2. Twin Hew** — dual-axe builder.<br>**3. Skullsplit Leap** — leap in and inflict bleeding.<br>**4. Exhausting Swing** — brutal strike that dumps Rage for burst.<br>**5. Bloodhowl** — self-buff for speed and attack tempo.<br>**6. Grim Pursuit** — shrug off slows and chase harder.<br>**7. Reckless Arc** — spin attack that scales with Rage.<br>**8. No Respite** — finisher against bleeding targets.<br>**9. Doom Roar** — anti-fear, anti-peel shout.<br>**10. Final Reckoning** — ultimate frenzy; massive offense for a short duration, followed by a vulnerability crash. |
| **Glyphbinder**<br>old: Rune Priest | Positional support healer. Establishes **Runes** on allies, the ground, and key targets so fights are won by setup, not just spam healing. | **1. Rune of Mending** — direct heal; leaves a short HoT rune.<br>**2. Rune of Warding** — shield rune on an ally.<br>**3. Rune of Cleaving** — enemy mark that lowers armor.<br>**4. Anchor Sigil** — rune circle that snares or roots entrants.<br>**5. Oath Script** — buff rune granting damage or resistances.<br>**6. Master Rune of Hearth** — persistent healing totem/rune stone.<br>**7. Master Rune of Ruin** — delayed explosive rune zone.<br>**8. Stoneword** — knockback line of erupting sigils.<br>**9. Ancestor’s Favor** — refresh the nearest placed rune and cleanse its target.<br>**10. Ancestor Lexicon** — ultimate; all active runes pulse again at increased strength. |
| **Siegewright**<br>old: Engineer | Ranged control/artillery specialist. Uses **Pressure** and deployables to shape space and punish predictable movement. | **1. Deploy Gunlet** — place a chosen turret mode.<br>**2. Crank Charge** — overclock current deployable; builds Pressure.<br>**3. Buckshot Salvo** — close cone blast for self-defense.<br>**4. Fragment Bomb** — thrown AoE explosive.<br>**5. Harpoon Line** — pull or tether tool.<br>**6. Landmine Satchel** — trap with knock-up or stagger.<br>**7. Grapnel Traverse** — zip move to reposition.<br>**8. Armor Piercer** — charged rifle shot through lines.<br>**9. Ironstorm Battery** — turret-assisted barrage that consumes Pressure.<br>**10. Fortified Redoubt** — ultimate emplacement that upgrades the turret, grants cover, and dominates a chokepoint. |

**High Elf**

| Class | Intended playstyle | Ten-ability kit |
|---|---|---|
| **Blade Savant**<br>old: Swordmaster | Form-chaining tank. Cycles **Opening → Rising → Perfect** stances to create a rhythmic defense/offense dance. | **1. Opening Form** — entry strike; starts stance chain.<br>**2. Rising Form** — advancing cut that improves the chain.<br>**3. Perfect Form** — finisher slash; best after proper sequencing.<br>**4. Warding Arc** — parry cone versus frontal attacks.<br>**5. Moonstep** — elegant sidestep; next form improves automatically.<br>**6. Enchanted Edge** — magic-imbued blade stance.<br>**7. Spiral Guard** — circular peel attack around self.<br>**8. Mindward** — party anti-magic buffer/cleanse.<br>**9. Aether Crossing** — dash-through slash to reposition lines.<br>**10. Sevenfold Kata** — ultimate stance recital; rapid chained strikes while locked in Perfect Form. |
| **Pride Warden**<br>old: White Lion | Melee hunter with a bonded beast. Wins by coordinating master-and-companion pressure, not by solo button mashing. | **1. Hunter’s Mark** — identify prey; pet gains bonus aggression.<br>**2. Pounce** — self-and-companion engage.<br>**3. Pack Rend** — synchronized bleed combo.<br>**4. Guardian Roar** — pet peel/taunt tool.<br>**5. Flanker’s Path** — command the beast to circle behind the target.<br>**6. Trophy Axe** — high-commitment cleave into isolated foes.<br>**7. Wild Bond** — heal and speed boost for hunter and beast.<br>**8. Snare Net** — ranged root setup.<br>**9. King’s Leap** — companion knockdown followed by your finisher.<br>**10. Pride Unleashed** — ultimate; companion becomes empowered and opens alternate commands for a short hunt phase. |
| **Aether Sage**<br>old: Archmage | Hybrid healer-damage caster. Balances two flowing reserves so offense fuels support and support fuels offense. | **1. Starshard** — damage bolt; builds Healing Echo.<br>**2. Verdant Current** — heal; builds Arcane Echo.<br>**3. Energy Weave** — convert stored Echo into cost reduction.<br>**4. Moonwell** — placed field that heals allies and lightly harms foes.<br>**5. Sunpierce** — beam damage that echoes partial healing.<br>**6. Merciful Veil** — shield and cleanse spell.<br>**7. Comet Snare** — delayed root burst.<br>**8. Tranquil Drift** — blink with a trailing ward.<br>**9. High Concord** — next spell double-casts its opposite polarity effect.<br>**10. Celestial Equinox** — ultimate equilibrium state where offensive spells echo healing and healing spells echo damage. |
| **Veil Ranger**<br>old: Shadow Warrior | Mobile stance archer. Alternates long-range pressure, moving skirmish fire, and opportunistic close assault. | **1. Longdraw** — stand-and-fire precision shot.<br>**2. Running Shot** — mobile bow attack while moving.<br>**3. Shadow Rush** — sudden close-range dash slash.<br>**4. Barbed Volley** — bleed-inflicting arrow fan.<br>**5. Mist Walk** — camouflage reposition tool.<br>**6. Eye Pierce** — interrupt/silence shot.<br>**7. Waylay Trap** — ground snare/ambush trap.<br>**8. Moonshot** — arcing reveal arrow for scouting.<br>**9. Vengeance Mark** — target takes bonus damage after stance changes.<br>**10. Eclipse Hunt** — ultimate three-part chain: aimed shot, closing dash, finishing strike. |

## Destruction class plans

The Destruction grounding is equally clear in the current class references: Chaos careers emphasize dark-gift tanking, mutation-driven melee, daemon/disc-like artillery, and mark/harbinger ritual support; Greenskin careers emphasize blunt armored disruption, pet-led ranged harassment, hybrid support magic, and escalating melee frenzy; Dark Elf careers emphasize blood-frenzy assassination, hatred-fueled offense-tanking, dark-magic risk casting, and melee siphon healing. citeturn14search0turn8search2turn8search3turn10search2turn11search0turn10search3turn9search2turn13search8turn11search2turn14search1turn12search2turn12search0

**Chaos**

| Class | Intended playstyle | Ten-ability kit |
|---|---|---|
| **Dreadsworn**<br>old: Chosen | Aura-debuff tank. Applies oppressive **Dark Gifts** and curses that make the whole enemy formation worse at fighting. | **1. Aura of Dread** — passive enemy offense reduction nearby.<br>**2. Aura of Ruin** — nearby resist/armor debuff field.<br>**3. Aura of Dominion** — team control-resistance aura.<br>**4. Hexbrand Cleave** — spreads curse tags in melee.<br>**5. Black Bastion** — heavy defensive shield stance.<br>**6. Tyrant’s Advance** — unstoppable march forward.<br>**7. Sunder Faith** — anti-caster taunt/silence.<br>**8. Warp Riposte** — counter hit after a successful block.<br>**9. Harrowing Roar** — fear pulse that detonates stacked curses.<br>**10. Crown of Ruin** — ultimate stance with all three auras active at reduced strength plus periodic curse bursts. |
| **Warped Reaver**<br>old: Marauder | Form-switching melee disruptor. Chooses mutations to answer the battlefield moment: shred, crush, or pull. | **1. Mutate Claw** — enter high-speed shredding form.<br>**2. Mutate Crusher** — enter armor-breaking bruiser form.<br>**3. Mutate Tendril** — enter reach-and-pull form.<br>**4. Flesh Hook** — drag prey inward.<br>**5. Ravage Burst** — mutation-specific spender attack.<br>**6. Hideous Regrowth** — regenerative self-heal.<br>**7. Warpsprint** — burst chase movement.<br>**8. Bone Splinter** — cone rupture that bleeds and lowers armor.<br>**9. Mutation Shift** — fast form swap that empowers the next cast.<br>**10. Apotheosis of Change** — ultimate mutation fusion, briefly borrowing all mutation bonuses at once. |
| **Void Magister**<br>old: Magus | Deployable occult artillery. Dominates space through an **Idol** that modifies nearby spells and zones. | **1. Summon Idol** — deploy the current idol form.<br>**2. Warp Bolt** — basic ranged nuke.<br>**3. Entropic Field** — slow/damage field centered on the idol.<br>**4. Rift Pull** — draw enemies toward the idol.<br>**5. Daemonfire Orb** — projectile that bursts harder near the idol.<br>**6. Hover Disc** — strafe mobility and kiting tool.<br>**7. Unmake Armor** — dark debuff on a key target.<br>**8. Feed the Idol** — overcharge summon by paying your own resource.<br>**9. Warp Storm** — sustained AoE channel from idol location.<br>**10. Grand Conjunction** — ultimate; idol fractures into a large tri-layer zone of pull, burn, and debuff. |
| **Ruin Oracle**<br>old: Zealot | Debuff-healer ritualist. Prepares allies with **Marks**, burdens enemies with **Harbingers**, then converts enemy suffering into team advantage. | **1. Mark of Vigor** — ally buff mark.<br>**2. Harbinger of Frailty** — enemy DoT/debuff mark.<br>**3. Soul Drain Rite** — siphon from a harbinger target to empower a marked ally.<br>**4. Fetish Ward** — totem pulse for resist or cleanse.<br>**5. Madness Cant** — cone disorientation chant.<br>**6. Blessing of Ruin** — lifesaving ward on an ally.<br>**7. Scourging Sigil** — cursed ground zone.<br>**8. Tether of Agony** — pain link between combatants.<br>**9. Prophecy of Ash** — delayed detonation on afflicted foes.<br>**10. Altar of the Raven** — ultimate ritual that upgrades all active marks and harbingers in a large area. |

**Greenskin**

| Class | Intended playstyle | Ten-ability kit |
|---|---|---|
| **Warbrute**<br>old: Black Orc | Combo-tank bruiser. Advances through **Plan** states so simple buttons become better when used in the right order. | **1. Sneaky Start** — opener; enters Good Plan.<br>**2. Proper Wallop** — chain attack; advances the Plan.<br>**3. Biggest Finish** — finisher; best from top Plan tier.<br>**4. Shut It!** — shield bash silence.<br>**5. Get Stuck In** — charge into melee.<br>**6. Wot’s Yours Is Mine** — steal armor/block from target.<br>**7. Keep Smashin** — sustain buff on hit.<br>**8. Boss Stomp** — AoE knockdown.<br>**9. You Watch Me!** — bodyguard-style ally protection shout.<br>**10. Boss’s Big Idea** — ultimate; instantly enters top Plan state and chains empowered finishers for a short brawl window. |
| **Fang Herder**<br>old: Squig Herder | Ranged pet skirmisher. Uses beast variants, mobility, and harassment to keep enemies off balance. | **1. Loose Fang** — send companion to harry a target.<br>**2. Skewa Shot** — armor-piercing arrow.<br>**3. Bouncin’ Escape** — hop backward while firing.<br>**4. Bait Bag** — lure trap that erupts into a bite swarm.<br>**5. Spit Fang** — acid-spitting pet stance.<br>**6. Hound Fang** — fast chaser pet stance.<br>**7. Big Chompa** — heavy leap-and-knockdown companion attack.<br>**8. Needle Rain** — moving arrow volley.<br>**9. Gobbo Prod** — force the pet into a frenzy at the cost of control.<br>**10. Fang Stampede** — ultimate multi-beast rush across a lane or choke. |
| **Bog Hexer**<br>old: Shaman | Mobile hybrid support caster. Offense fuels better healing and healing fuels nastier tricks. | **1. Green Zap** — damage builder for support power.<br>**2. Patch-Up** — heal builder for hex power.<br>**3. Crooked Beam** — lifetap beam.<br>**4. Bog Hop** — bouncing reposition.<br>**5. Sticky Curse** — slow and anti-heal.<br>**6. Lucky Idol** — supportive idol/totem field.<br>**7. Brain Banga** — interrupt projectile.<br>**8. Foul Brew** — bouncing heal-or-harm concoction.<br>**9. Mixed Medicine** — next cast echoes an opposite-type effect.<br>**10. Big Green Turnabout** — ultimate window where offensive casts splash small heals and healing casts lash nearby enemies. |
| **Cleaver**<br>old: Choppa | Pure aggression melee bruiser. Builds frenzy fast, cashes it into heavy commit tools, and dares enemies to survive the storm. | **1. Whirly Chop** — spinning builder attack.<br>**2. Get Over ’Ere** — hook pull.<br>**3. Mad Dash** — reckless forward rush.<br>**4. Heavy Chop** — big Rage-dump strike.<br>**5. Can’t Stop Me** — anti-CC rage button.<br>**6. Deep Cutz** — bleed cleave.<br>**7. Facebreaker** — stun/uppercut hit.<br>**8. Keep Swingin** — temporary on-hit sustain.<br>**9. Smash Pile** — leap slam into clustered enemies.<br>**10. Red Mist** — ultimate frenzy; huge cleaving pressure followed by a defensive hangover. |

**Dark Elf**

| Class | Intended playstyle | Ten-ability kit |
|---|---|---|
| **Blood Dancer**<br>old: Witch Elf | Hypermobile assassin. Builds **Bloodlust** through poison and rapid strikes, then cashes out into lethal backline executions. | **1. Vein Slice** — stealth opener; builds Bloodlust.<br>**2. Poison Kiss** — venom application attack.<br>**3. Shadow Prowl** — vanish/re-stealth movement.<br>**4. Razor Waltz** — rapid multi-dagger flurry.<br>**5. Crippling Cut** — slow plus healing reduction.<br>**6. Heartseeker** — lunge toward marked prey.<br>**7. Red Caress** — Bloodlust-spending execute.<br>**8. Mirror Veil** — brief evasive untargetability step.<br>**9. Suffering Bloom** — detonate active poisons around the victim.<br>**10. Crimson Ecstasy** — ultimate blood-frenzy; sustained flank bonuses and accelerated combo gain. |
| **Dread Guard**<br>old: Blackguard | Offensive anti-mage tank. Builds **Hatred** while staying in the enemy’s face and turns that emotion into disruption, pursuit, and resistance. | **1. Spite Lash** — spear lash; builds Hatred.<br>**2. Malice Guard** — designate a prey target for elevated Hatred gain.<br>**3. Void Buckler** — spell block/reflect defense.<br>**4. Glaive Hook** — pull and disrupt positioning.<br>**5. Cruel Intercept** — leap to ally, intercept, then strike back.<br>**6. Sunder Grace** — lowers enemy parry/disrupt.<br>**7. Torment Cage** — taunt plus anti-escape field.<br>**8. Bitter Harvest** — Hatred-spending sustain tool.<br>**9. Harrow Pike** — long thrust line attack.<br>**10. Throne’s Contempt** — ultimate prey hunt; strong anti-magic and relentless chase pressure on one target. |
| **Dusk Weaver**<br>old: Sorceress | Risk-caster glass cannon. Builds **Dark Power** for bigger output while flirting with backlash and self-harm. | **1. Umbral Bolt** — safe ranged builder.<br>**2. Chill of Dusk** — snare and lingering pain spell.<br>**3. Black Shard** — heavy nuke; adds Dark Power quickly.<br>**4. Gloom Step** — blink that leaves a curse pool.<br>**5. Agony Thread** — debuff increasing incoming crit harm.<br>**6. Soul Freeze** — root with shatter follow-up.<br>**7. Void Rain** — cursed ground AoE.<br>**8. Cruel Harvest** — vent Dark Power for safer next casts.<br>**9. Backlash Surge** — weaponize your accumulated instability in a local burst.<br>**10. Midnight Cataclysm** — ultimate storm; massive devastation, followed by a self-backlash risk spike if mismanaged. |
| **Crimson Acolyte**<br>old: Disciple of Khaine | Melee siphon-healer. Gains **Essence** in close combat and redistributes stolen vitality to allies. | **1. Siphon Cut** — melee builder for Essence.<br>**2. Blood Rite** — targeted heal that spends Essence.<br>**3. Pain Mirror** — target mark causing enemy suffering to feed you.<br>**4. Razor Prayer** — aura granting lifesteal to nearby allies.<br>**5. Cruel Embrace** — pull target inward.<br>**6. Scarlet Step** — rush slash and reposition.<br>**7. Borrowed Vigor** — steal stats from foe for team gain.<br>**8. Covenant of Knives** — spinning AoE lifetap.<br>**9. Dark Communion** — group heal over time at Essence cost.<br>**10. Feast of the Shrine** — ultimate altar state converting much of your damage into large-area ally healing. |

## Technical blueprint for implementation

The class plans above will stay maintainable only if you author them as **ability templates plus class-specific parameters**, not as 240 bespoke snowflakes.

A practical approach is to define roughly a dozen reusable families: risk caster, verdict assassin, commander tank, melee healer, reactive oath tank, berserker, rune/mark support, deployable artillery, stance-chain tank, bonded-beast hunter, balance caster, and mobile skirmisher. Several of your classes naturally fall into mirrored families already. That makes balancing faster because each pair can share target budget, counterplay rules, and animation templates even when the fantasy and VFX differ. The underlying research supports this kind of separation: tags, effects, attributes, and reusable tasks are exactly what data-driven systems use to keep large ability vocabularies coherent. citeturn19view0turn19view1turn19view2turn19view3turn19view4

A solid per-ability schema would look like this:

```json
{
  "id": "empire.ember_arcanist.cinder_lance",
  "classFamily": "risk_caster",
  "slot": 2,
  "resource": { "builds": "Heat", "amount": 12 },
  "cooldownSec": 5,
  "tags": [
    "Ability.Magic.Fire",
    "Target.Single",
    "Range.25",
    "Consumes.GCD",
    "Breaks.Stealth"
  ],
  "animation": {
    "clip": "cast_short",
    "upperBodyOnly": true,
    "notifyWindows": [
      { "name": "release", "start": 0.34, "end": 0.38 }
    ]
  },
  "targeting": {
    "shape": "projectile",
    "speed": 26.0,
    "radius": 0.2,
    "tracePolicy": "server_auth"
  },
  "effects": [
    { "type": "damage", "school": "fire", "coef": 1.1 },
    { "type": "status", "apply": "burning", "duration": 4.0 }
  ],
  "vfxSockets": ["staff_tip", "hand_r"],
  "cancelRules": {
    "blockedBy": ["State.Silenced", "State.Stunned"],
    "appliesOwnerTags": ["State.Casting"]
  }
}
```

That schema aligns to the strongest patterns in the research: hierarchical tags, explicit execution controls, effect payloads, and animation tasks/windows. citeturn19view1turn19view2turn19view5

For your animation contract, I would expand your current clip taxonomy into a much more combat-ready set: `locomotion_idle`, `combat_idle`, `turn_in_place`, `draw_weapon`, `light_attack_a/b/c`, `heavy_attack`, `cast_short`, `cast_long`, `shoot_standing`, `shoot_moving`, `block`, `parry`, `dodge_left/right/back`, `hit_light`, `hit_heavy`, `knockdown`, `recover`, and class-signature ultimates. Use Notify Windows for active hit frames and release timing; use layered animation so moving-and-shooting or moving-and-casting does not require bespoke full-body clips for every state combination. citeturn19view5turn19view6

For the modular body and equipment blueprint, the most important technical rule is this: **every swappable part must conform to one canonical skeleton, one canonical neutral pose, and one masking/spec contract.** Three.js requires correct skin indices and weights, and shared-skeleton setups are explicitly supported through skinned mesh binding patterns. UE’s modular guidance shows the trade-off space between leader-pose, copy-pose, and runtime merge strategies, while Mutable highlights hidden surface removal and mesh/texture merging as key optimizations. citeturn21view0turn21view1turn21view3

For your runtime specifically, I would use this contract:

| Runtime concern | Recommendation |
|---|---|
| **Body and gear deformation** | one master skeleton, copied weights to each armor piece |
| **Attachment strategy** | author gear as skinned overlays, not static props for combat use |
| **Body clipping** | use hidden-body masks per slot under armor |
| **Weapon/VFX anchors** | standardized sockets: `weapon_r`, `offhand_l`, `staff_tip`, `muzzle`, `chest_core`, `back`, `cape_root`, `ground_anchor` |
| **Hit confirmation** | authored traces and simple collision proxies, never raw render mesh |
| **Animation cloning** | clone skinned characters through skeleton-safe utilities |
| **Culling/collision bounds** | update animated skinned bounds when needed |

That last point matters more than many teams realize. Three.js notes that the bounding box of a `SkinnedMesh` is not automatically computed, and that if the skinned mesh is animated the bounding box should be recomputed to reflect current animation state. If your current exports ever appear clipped, culled early, or mis-measured in runtime checks, that is one likely source. citeturn21view0

For visual quality, the art pass should aim for **readable realism** rather than maximal ornamentation. Riot’s clarity article is useful here: readability at distance depends on depth separation and silhouette strength, not just material richness. Combine that with hidden-surface removal and draw-call discipline, and your armor can look materially richer without becoming visually mushy. citeturn20view0turn21view3

The fastest build order for your team is:

| Phase | Deliverable |
|---|---|
| **Combat schema pass** | tags, costs, cooldowns, effect types, target shapes, class resources |
| **Animation contract pass** | notify windows, blend rules, active frames, locomotion overlays |
| **Mirror-family pass** | 12 system templates shared across the 24 classes |
| **Class content pass** | implement the 240 proposed abilities as template instances |
| **Art integration pass** | weapon sockets, VFX anchors, body masking, slot-safe armor |
| **Feel/polish pass** | hit-stop, anticipation, camera shake, VFX readability, audio layering |

## Open questions and limitations

I could inspect the uploaded export pipeline, but I did **not** have the full game runtime or gameplay codebase in the upload, so I could not verify your current hotbar logic, networking model, AI ability use, or the exact collision/hit-confirmation layer.

I grounded class fantasy against current Return of Reckoning career references because they are accessible and comprehensive, but the actual ability names, renamed classes, and combat kits in this report are **original design proposals**, not canonical reproductions. That is intentional for both gameplay flexibility and IP distancing. citeturn22view0turn14search3turn23search15turn5search3turn23search12turn14search0turn8search2turn8search3turn10search2