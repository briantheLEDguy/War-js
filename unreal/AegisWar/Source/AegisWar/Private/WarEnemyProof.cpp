#include "WarEnemyProof.h"
#include "WarEnemy.h"
#include "WarNpcEquipment.h"
#include "Components/StaticMeshComponent.h"
#include "WarEnemyStateSubsystem.h"
#include "WarCharacter.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarZoneStreamingSubsystem.h"
#include "WarZoneAnchor.h"
#include "WarZonePortal.h"
#include "AbilitySystemComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"

bool UWarEnemyProof::ShouldCreateSubsystem(UObject* Outer) const
{ return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(), TEXT("WarEnemyProof")); }
TStatId UWarEnemyProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarEnemyProof, STATGROUP_Tickables); }

void UWarEnemyProof::Finish(bool bPassed, const FString& Detail)
{
    bFinished = true;
    UE_LOG(LogTemp, Display, TEXT("WAR_ENEMY_PROOF passed=%d stage=%d hits=%d %s"), bPassed, Stage, Hits, *Detail);
    const FString Directory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("EnemyProof"));
    IFileManager::Get().MakeDirectory(*Directory, true);
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("{\"passed\":%s,\"stage\":%d,\"hits\":%d,\"enemyDamagedPlayer\":%s,\"productionAccepted\":false}"),
        bPassed ? TEXT("true") : TEXT("false"), Stage, Hits, bDamagedPlayer ? TEXT("true") : TEXT("false")), *FPaths::Combine(Directory, TEXT("report.json")));
    FPlatformMisc::RequestExitWithStatus(false, bPassed ? 0 : 1);
}

void UWarEnemyProof::Tick(float DeltaSeconds)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = GetWorld()->GetTimeSeconds(); if (Now < NextStep) return;
    auto* PC = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Pawn = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    auto* State = PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
    auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
    if (!Pawn || !State || !Pawn->IsVisualReady() || !Streaming)
    { if (Now > 90) Finish(false, TEXT("Player unavailable")); return; }
    if (Deadline > 0 && Now > Deadline) { Finish(false, TEXT("Stage timed out")); return; }
    FString Error;
    const FName Sun(TEXT("sunmeadow_march")), Other(TEXT("cinderfen_outskirts")), Id(TEXT("sunmeadow_march_west_raider_1"));
    AWarEnemy* Enemy = nullptr; int32 Count = 0;
    for (TActorIterator<AWarEnemy> It(GetWorld()); It; ++It)
        if (It->ZoneId == Sun) { ++Count; if (It->EnemyId == Id) Enemy = *It; }
    const auto HasOneWeapon = [](AWarEnemy* Actor) {
        if (!Actor) return false;
        TInlineComponentArray<UStaticMeshComponent*> Components; Actor->GetComponents(Components);
        int32 WeaponCount = 0;
        for (const auto* Component : Components)
            if (UWarNpcEquipmentLibrary::IsGeneratedAttachment(Component) && Component->GetStaticMesh()) ++WeaponCount;
        return WeaponCount == 1;
    };
    const auto Place = [&](FVector Point) {
        FHitResult Hit; FCollisionQueryParams Params(SCENE_QUERY_STAT(WarEnemyProofFloor), false, Pawn);
        if (Enemy) Params.AddIgnoredActor(Enemy);
        if (!GetWorld()->LineTraceSingleByChannel(Hit, Point + FVector(0,0,1500), Point - FVector(0,0,2500), ECC_Visibility, Params)) return false;
        Pawn->GetCharacterMovement()->StopMovementImmediately();
        return Pawn->TeleportTo(Hit.ImpactPoint + FVector(0,0,98), FRotator::ZeroRotator);
    };
    if (Stage == 0)
    {
        if (!Streaming->QueueGmZone(PC, Sun, Error)) { Finish(false, Error); return; }
        Stage = 1; Deadline = Now + 45; return;
    }
    if (Stage == 1)
    {
        if (State->GetCurrentZone() != Sun || !Streaming->IsZoneReady(Sun)) return;
        if (!Enemy || Count != 3 || !Enemy->IsContentReady()) { Finish(false, TEXT("Three exact raiders not loaded")); return; }
        if (!HasOneWeapon(Enemy)) { Finish(false, TEXT("Raider weapon missing or duplicated")); return; }
        Home = Enemy->GetHome();
        if (!Place(Home + FVector(0,-1200,0))) { Finish(false, TEXT("Could not reach source encounter")); return; }
        const float Before = State->GetAttributes()->GetMana();
        Pawn->RequestTargetStrike(Enemy);
        if (State->GetAttributes()->GetMana() != Before || Enemy->GetHealth() != 150)
        { Finish(false, TEXT("Out of range strike mutated combat state")); return; }
        // High proof vitals let damage observation run without replacing the tested pawn.
        State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(), 1000);
        State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(), 1000);
        Stage = 2; Deadline = Now + 20; return;
    }
    if (Stage == 2)
    {
        if (!Enemy || Enemy->GetTarget() != Pawn || FVector::Dist2D(Pawn->GetActorLocation(), Enemy->GetActorLocation()) > 310) return;
        if (FVector::Dist2D(Home, Enemy->GetActorLocation()) < 500) { Finish(false, TEXT("Raider did not chase")); return; }
        if (!Place(Home + FVector(0,-4200,0))) { Finish(false, TEXT("Could not leave leash")); return; }
        Stage = 3; Deadline = Now + 10; return;
    }
    if (Stage == 3)
    {
        if (!Enemy || Enemy->GetTarget() || FVector::Dist2D(Home, Enemy->GetActorLocation()) > 5) return;
        if (Enemy->GetHealth() != 150 || !Place(Home + FVector(0,-250,0))) { Finish(false, TEXT("Leash did not restore home health")); return; }
        State->SetCurrentZoneTrusted(Other);
        if (Pawn->CanStrikeTarget(Enemy)) { Finish(false, TEXT("Cross-zone target accepted")); return; }
        State->SetCurrentZoneTrusted(Sun);
        TArray<FWarInventoryItem> Fill;
        for (int32 Slot = 0; Slot < WarInventory::Capacity; ++Slot)
        {
            FWarInventoryItem Item; Item.Key = FName(*FString::Printf(TEXT("enemy_proof_fill_%d"), Slot));
            Item.Kind = TEXT("misc"); Item.Quantity = 99; Fill.Add(Item);
        }
        if (!State->GrantRewards(FGuid::NewGuid(), Fill, Error) || State->GetInventory().Items.Num() != WarInventory::Capacity)
        { Finish(false, TEXT("Full inventory setup failed")); return; }
        const auto Before = State->GetInventory(); FWarInventoryItem Invalid; Invalid.Quantity = -1;
        if (State->AwardEnemyKillTrusted(Sun, Id, FGuid::NewGuid(), {Invalid}, Error)
            || !FWarInventorySnapshot::StaticStruct()->CompareScriptStruct(&Before, &State->GetInventory(), 0))
        { Finish(false, TEXT("Invalid reward was not atomic")); return; }
        XpBefore = State->GetInventory().CharacterProgression.Xp;
        HealthBefore = State->GetAttributes()->GetHealth();
        Pawn->RequestTargetStrike(Enemy); ++Hits; ManaAfter = State->GetAttributes()->GetMana();
        if (Enemy->GetHealth() != 150) { Finish(false, TEXT("Strike damaged before windup")); return; }
        Stage = 4; NextStep = Now + Pawn->GetAbilityAnimationDuration(TEXT("attack_melee")) * .8 + .1; Deadline = Now + 30; return;
    }
    if (Stage == 4)
    {
        Pawn->RequestTargetStrike(Enemy);
        if (!Enemy || Enemy->GetHealth() != 130 || State->GetAttributes()->GetMana() != ManaAfter)
        { Finish(false, TEXT("Cooldown allowed a repeated strike")); return; }
        Stage = 5; NextStep = Now + 2; return;
    }
    if (Stage == 5)
    {
        if (!Enemy) { Finish(false, TEXT("Encounter vanished")); return; }
        bDamagedPlayer |= State->GetAttributes()->GetHealth() < HealthBefore;
        if (!Enemy->IsDead()) { Pawn->RequestTargetStrike(Enemy); ++Hits; NextStep = Now + 2.1; return; }
        const auto& Life = GetWorld()->GetSubsystem<UWarEnemyStateSubsystem>()->FindOrCreate(Sun, Id, 150);
        DeathEvent = Life.Event; DeathAt = Now;
        const auto After = State->GetInventory();
        if (!bDamagedPlayer || Hits != 8 || After.CharacterProgression.Xp != XpBefore + 50
            || State->AwardEnemyKillTrusted(Sun, Id, DeathEvent, {}, Error)
            || !FWarInventorySnapshot::StaticStruct()->CompareScriptStruct(&After, &State->GetInventory(), 0)
            || Enemy->ReceiveStrike(Pawn))
        { Finish(false, TEXT("Death attribution/repeat rejection failed")); return; }
        UE_LOG(LogTemp, Display, TEXT("WAR_ENEMY_LIVE_KILL hits=%d xp=50 pendingLoot=%d"), Hits, After.PendingRewards.Num());
        if (!Streaming->QueueGmZone(PC, Other, Error)) { Finish(false, Error); return; }
        Stage = 6; Deadline = Now + 30; return;
    }
    if (Stage == 6)
    {
        if (State->GetCurrentZone() != Other || Enemy) return;
        const auto& Life = GetWorld()->GetSubsystem<UWarEnemyStateSubsystem>()->FindOrCreate(Sun, Id, 150);
        if (Life.Event != DeathEvent || Life.Health != 0 || Life.RespawnAt < DeathAt + 14.9)
        { Finish(false, TEXT("Unloading reset the death record")); return; }
        UE_LOG(LogTemp, Display, TEXT("WAR_ENEMY_UNLOAD_PRESERVED"));
        if (!Streaming->QueueGmZone(PC, Sun, Error)) { Finish(false, Error); return; }
        Stage = 7; Deadline = Now + 40; return;
    }
    if (Stage == 7)
    {
        if (State->GetCurrentZone() != Sun && !Streaming->HasPending(Pawn))
        {
            for (TActorIterator<AWarZonePortal> It(GetWorld()); It; ++It)
            {
                if (!It->DestinationRouteId.ToString().StartsWith(TEXT("sunmeadow_march_to_"))) continue;
                FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(WarEnemyReturnDiagnostic), false, Pawn);
                const bool Found = GetWorld()->LineTraceSingleByChannel(Hit, It->ArrivalLocation + FVector(0,0,5000),
                    It->ArrivalLocation - FVector(0,0,5000), ECC_WorldStatic, Query);
                UE_LOG(LogTemp, Display, TEXT("WAR_ENEMY_RETURN_GROUND route=%s arrival=%s hit=%d point=%s normal=%s actor=%s"),
                    *It->RouteId.ToString(), *It->ArrivalLocation.ToString(), Found, *Hit.ImpactPoint.ToString(),
                    *Hit.ImpactNormal.ToString(), *GetNameSafe(Hit.GetActor()));
                break;
            }
            Finish(false, TEXT("Return travel failed: ") + PC->GetWorldEditMessage() + TEXT(" / ") + PC->GetZoneTravelStatus()); return;
        }
        NextStep = Now + 2;
        UE_LOG(LogTemp, Display, TEXT("WAR_ENEMY_RETURN zone=%s ready=%d enemy=%d content=%d health=%.1f now=%.1f death=%.1f pos=%s"),
            *State->GetCurrentZone().ToString(), Streaming->IsZoneReady(Sun), Enemy != nullptr, Enemy && Enemy->IsContentReady(),
            Enemy ? Enemy->GetHealth() : -1, Now, DeathAt, Enemy ? *Enemy->GetActorLocation().ToString() : TEXT("absent"));
        if (State->GetCurrentZone() != Sun || !Enemy || !Enemy->IsContentReady()) return;
        const auto& Life = GetWorld()->GetSubsystem<UWarEnemyStateSubsystem>()->FindOrCreate(Sun, Id, 150);
        if (Now < DeathAt + 14.9 && (!Enemy->IsDead() || Life.Event != DeathEvent))
        { Finish(false, TEXT("Reload bypassed respawn cooldown")); return; }
        if (Enemy->IsDead()) return;
        if (!HasOneWeapon(Enemy)) { Finish(false, TEXT("Reload/respawn lost or duplicated equipment")); return; }
        if (Life.Event == DeathEvent || Enemy->GetHealth() != 150 || FVector::Dist2D(Enemy->GetActorLocation(), Home) > 5)
        { Finish(false, TEXT("Respawn did not begin a new life at home")); return; }
        Finish(true, TEXT("range, zone, chase, leash, cooldown, damage, atomic reward, duplicate death, unload/reload and respawn passed"));
    }
}
