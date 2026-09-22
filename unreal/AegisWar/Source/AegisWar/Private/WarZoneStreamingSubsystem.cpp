#include "WarZoneStreamingSubsystem.h"
#include "WarZoneAnchor.h"
#include "WarZonePortal.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarCityNpc.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarGameMode.h"
#include "Engine/LevelStreaming.h"
#include "Engine/Level.h"
#include "Engine/Brush.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/NetConnection.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"

bool UWarZoneStreamingSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{ return Type == EWorldType::Game || Type == EWorldType::PIE; }
TStatId UWarZoneStreamingSubsystem::GetStatId() const
{ RETURN_QUICK_DECLARE_CYCLE_STAT(UWarZoneStreamingSubsystem, STATGROUP_Tickables); }

bool UWarZoneStreamingSubsystem::CanContinue(bool bSamePawn, bool bAlive, bool bVisualReady,
    double Distance, double Radius, double Now, double Deadline)
{
    return bSamePawn && bAlive && bVisualReady && FMath::IsFinite(Distance) && Distance >= 0
        && FMath::IsFinite(Radius) && Radius > 0 && Distance <= Radius
        && FMath::IsFinite(Now) && FMath::IsFinite(Deadline) && Now < Deadline;
}

bool UWarZoneStreamingSubsystem::RequiresActorCollisionReadiness(const AActor* Actor)
{
    // The level's builder brush is an editor construction helper without a runtime physics body.
    // Other brushes (including blocking volumes) still participate in readiness.
    return IsValid(Actor) && Actor->GetActorEnableCollision()
        && (!Actor->GetLevel() || Actor != Actor->GetLevel()->GetDefaultBrush());
}

bool UWarZoneStreamingSubsystem::IsZoneReady(FName Zone, const APlayerController* Player, FString* OutReason) const
{
    if (OutReason) OutReason->Reset();
    const auto Waiting = [OutReason](const FString& Reason) { if (OutReason) *OutReason = Reason; return false; };
    const auto* Anchor = AWarZoneAnchor::FindById(GetWorld(), Zone);
    if (!Anchor) return Waiting(TEXT("Destination anchor is missing."));
    for (const FName Package : Anchor->ContentLevels)
    {
        const auto* Level = UGameplayStatics::GetStreamingLevel(GetWorld(), Package);
        if (!Level || !Level->IsLevelLoaded() || !Level->IsLevelVisible())
            return Waiting(FString::Printf(TEXT("Level is not visible: %s"), *Package.ToString()));
        // UE can expose a visible streamed level before its async physics bodies finish.
        // Admission must wait for blocking collision, including on a fast return to a zone.
        for (const AActor* Actor : Level->GetLoadedLevel()->Actors)
        {
            if (const auto* Npc = Cast<AWarCityNpc>(Actor); Npc && !Npc->IsEquipmentReady())
                return Waiting(FString::Printf(TEXT("NPC equipment is not ready: %s"), *Npc->GetName()));
            if (!RequiresActorCollisionReadiness(Actor)) continue;
            TInlineComponentArray<UPrimitiveComponent*> Components; Actor->GetComponents(Components);
            for (const auto* Component : Components)
                if (Component->IsRegistered() && Component->IsQueryCollisionEnabled()
                    && (Component->GetCollisionResponseToChannel(ECC_WorldStatic) == ECR_Block
                        || Component->GetCollisionResponseToChannel(ECC_Pawn) == ECR_Block)
                    && (!Component->IsPhysicsStateCreated() || !Component->HasValidPhysicsState()
                        || Component->IsAsyncCreatePhysicsStateRunning()))
                    return Waiting(FString::Printf(TEXT("Collision is not ready: %s (%s)"), *Actor->GetName(), *Component->GetName()));
        }
        // Acknowledged engine visibility is required before a remote pawn can enter collision there.
        const auto* Connection = Player ? Player->GetNetConnection() : nullptr;
        if (Connection && !Connection->ClientVisibleLevelNames.Contains(Level->GetWorldAssetPackageFName()))
            return Waiting(FString::Printf(TEXT("Client is still loading: %s"), *Package.ToString()));
    }
    for (TActorIterator<AWarEnemy> It(GetWorld()); It; ++It)
        if (It->ZoneId == Zone && !It->IsContentReady())
            return Waiting(FString::Printf(TEXT("Enemy content is not ready: %s"), *It->GetName()));
    if (!Anchor->ContentLevels.IsEmpty())
    {
        // Body creation can finish before Chaos publishes it to scene queries. Probe the
        // authored arrivals too, rather than declaring readiness from registration alone.
        const FString Prefix = Zone.ToString() + TEXT("_to_");
        FCollisionQueryParams Query(SCENE_QUERY_STAT(WarZoneCollisionReady), false);
        if (Player && Player->GetPawn()) Query.AddIgnoredActor(Player->GetPawn());
        for (TActorIterator<AWarZonePortal> It(GetWorld()); It; ++It)
        {
            if (!It->bDestinationBuilt || !It->DestinationRouteId.ToString().StartsWith(Prefix)) continue;
            FHitResult Ground;
            if (!GetWorld()->LineTraceSingleByChannel(Ground, It->ArrivalLocation + FVector(0,0,5000),
                It->ArrivalLocation - FVector(0,0,5000), ECC_WorldStatic, Query) || Ground.ImpactNormal.Z < 0.7)
                return Waiting(FString::Printf(TEXT("Arrival floor is not ready: %s"), *It->DestinationRouteId.ToString()));
        }
    }
    return true;
}

bool UWarZoneStreamingSubsystem::EnsureZone(FName Zone, FString& Error)
{
    const auto* Mode = GetWorld()->GetAuthGameMode<AWarGameMode>();
    const auto* Anchor = AWarZoneAnchor::FindById(GetWorld(), Zone);
    if (!Mode || !Mode->IsDevelopmentSession() || !Anchor)
    { Error = TEXT("Zone loading requires a known development destination."); return false; }
    for (FName Package : Anchor->ContentLevels)
        if (!UGameplayStatics::GetStreamingLevel(GetWorld(), Package))
        { Error = TEXT("Destination content is unavailable. You remain in the current zone."); return false; }
    KeepUntil.Add(Zone, GetWorld()->GetTimeSeconds() + 5.0);
    for (FName Package : Anchor->ContentLevels)
    {
        auto* Level = UGameplayStatics::GetStreamingLevel(GetWorld(), Package);
        Level->SetShouldBeLoaded(true);
        Level->SetShouldBeVisible(true);
    }
    return true;
}

bool UWarZoneStreamingSubsystem::HasPending(const AWarCharacter* Character) const
{ return Pending.ContainsByPredicate([Character](const FPending& Row) { return Row.Character.Get() == Character; }); }
void UWarZoneStreamingSubsystem::Cancel(AWarCharacter* Character)
{ Pending.RemoveAll([Character](const FPending& Row) { return Row.Character.Get() == Character; }); }

bool UWarZoneStreamingSubsystem::QueueGmZone(AWarPlayerController* Player, FName Destination, FString& Error)
{
    auto* Character = Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
    if (!Player || !Player->CanUseGmTools() || !Character || Character->IsDead() || !Character->IsVisualReady())
    { Error = TEXT("GM travel is unavailable."); return false; }
    if (HasPending(Character)) { Error = TEXT("Travel is already loading. Move away to cancel."); return false; }
    if (!EnsureZone(Destination, Error)) return false;
    Pending.Add({nullptr, Character, Player, Destination, GetWorld()->GetTimeSeconds() + 30.0, true, Character->GetActorLocation()});
    Character->GetCharacterMovement()->StopMovementImmediately();
    if (Character->IsAutoRunning()) Character->ToggleAutoRun();
    Error = TEXT("Loading destination. Move away to cancel.");
    Player->ClientZoneTravelStatus(Error);
    UpdateStreaming(); return true;
}

bool UWarZoneStreamingSubsystem::QueuePortal(AWarZonePortal* Portal, AWarCharacter* Character,
    FName Destination, FString& Error)
{
    auto* Player = Character ? Cast<APlayerController>(Character->GetController()) : nullptr;
    if (!Portal || !Player || !EnsureZone(Destination, Error)) return false;
    const auto* Existing = Pending.FindByPredicate([Character](const FPending& Row) { return Row.Character.Get() == Character; });
    if (Existing)
    {
        Error = Existing->Portal.Get() == Portal ? TEXT("Loading destination. Move away to cancel.") : TEXT("Another portal is loading. Move away to cancel.");
        return false;
    }
    Pending.Add({Portal, Character, Player, Destination, GetWorld()->GetTimeSeconds() + 30.0});
    Character->GetCharacterMovement()->StopMovementImmediately();
    if (Character->IsAutoRunning()) Character->ToggleAutoRun();
    Error = TEXT("Loading destination. Move away to cancel.");
    if (auto* PC = Cast<AWarPlayerController>(Player)) PC->ClientZoneTravelStatus(Error);
    UpdateStreaming();
    return false; // The pawn has not traversed yet; completion revalidates the portal and landing.
}

void UWarZoneStreamingSubsystem::UpdateStreaming()
{
    const double Now = GetWorld()->GetTimeSeconds();
    TSet<FName> WantedZones;
    for (auto It = KeepUntil.CreateIterator(); It; ++It)
        if (It.Value() <= Now) It.RemoveCurrent(); else WantedZones.Add(It.Key());
    TMap<TWeakObjectPtr<APlayerController>, TSet<FName>> PlayerZones;
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        auto* Player = It->Get();
        if (!Player) continue;
        auto& Zones = PlayerZones.FindOrAdd(Player);
        if (const auto* State = Player->GetPlayerState<AWarPlayerState>()) Zones.Add(State->GetCurrentZone());
        if (const APawn* Pawn = Player->GetPawn())
            if (const auto* Anchor = AWarZoneAnchor::FindAt(GetWorld(), Pawn->GetActorLocation())) Zones.Add(Anchor->ZoneId);
        for (const auto& Row : Pending) if (Row.Player.Get() == Player) Zones.Add(Row.Destination);
        WantedZones.Append(Zones);
    }
    TSet<FName> WantedPackages;
    TSet<FName> ManagedPackages;
    for (TActorIterator<AWarZoneAnchor> It(GetWorld()); It; ++It)
    {
        for (FName Package : It->ContentLevels)
        {
            ManagedPackages.Add(Package);
            if (WantedZones.Contains(It->ZoneId)) WantedPackages.Add(Package);
        }
    }
    for (FName Package : ManagedPackages)
        if (auto* Level = UGameplayStatics::GetStreamingLevel(GetWorld(), Package))
        {
            const bool bWanted = WantedPackages.Contains(Package);
            Level->SetShouldBeLoaded(bWanted); Level->SetShouldBeVisible(bWanted);
        }
    for (const auto& Entry : PlayerZones)
    {
        auto* Player = Entry.Key.Get();
        if (!Player || Player->IsLocalController()) continue;
        TSet<FName> Wanted;
        for (FName Zone : Entry.Value)
            if (const auto* Anchor = AWarZoneAnchor::FindById(GetWorld(), Zone)) Wanted.Append(Anchor->ContentLevels);
        const auto* Previous = ClientPackages.Find(Player);
        for (FName Package : ManagedPackages)
            if (!Previous || Previous->Contains(Package) != Wanted.Contains(Package))
                if (auto* Level = UGameplayStatics::GetStreamingLevel(GetWorld(), Package))
                    Player->LevelStreamingStatusChanged(Level, Wanted.Contains(Package), Wanted.Contains(Package), false, INDEX_NONE);
        ClientPackages.Add(Player, MoveTemp(Wanted));
    }
    for (auto It = ClientPackages.CreateIterator(); It; ++It)
        if (!It.Key().IsValid() || !PlayerZones.Contains(It.Key())) It.RemoveCurrent();
}

void UWarZoneStreamingSubsystem::Tick(float DeltaTime)
{
    const auto* Mode = GetWorld()->GetAuthGameMode<AWarGameMode>();
    if (!GetWorld()->HasBegunPlay() || !Mode || !Mode->IsDevelopmentSession()) return;
    if (GetWorld()->GetTimeSeconds() < NextUpdateAt) return;
    NextUpdateAt = GetWorld()->GetTimeSeconds() + 0.1;
    UpdateStreaming();
    for (int32 Index = Pending.Num() - 1; Index >= 0; --Index)
    {
        const FPending Row = Pending[Index];
        auto* Portal = Row.Portal.Get(); auto* Character = Row.Character.Get(); auto* Player = Row.Player.Get();
        auto* GmPlayer = Row.bGm ? Cast<AWarPlayerController>(Player) : nullptr;
        const bool bValidRequest = Row.bGm ? GmPlayer && GmPlayer->CanUseGmTools() : Portal != nullptr;
        const FVector Source = Row.bGm ? Row.SourcePosition : Portal ? Portal->GetActorLocation() : FVector::ZeroVector;
        const double Radius = Row.bGm ? 250.0 : Portal ? Portal->Radius * Portal->GetActorScale3D().GetAbsMax() : 0.0;
        if (!bValidRequest || !Character || !Player || !CanContinue(Player->GetPawn() == Character,
            !Character->IsDead(), Character->IsVisualReady(), FVector::Dist(Character->GetActorLocation(), Source),
            Radius, GetWorld()->GetTimeSeconds(), Row.Deadline))
        {
            Pending.RemoveAt(Index);
            if (auto* PC = Cast<AWarPlayerController>(Player)) PC->ClientZoneTravelStatus(TEXT("Portal loading cancelled. Move into the portal to retry."));
            continue;
        }
        if (!IsZoneReady(Row.Destination, Player)) continue;
        Pending.RemoveAt(Index);
        if (GmPlayer)
        {
            GmPlayer->ClientZoneTravelStatus(FString());
            GmPlayer->ServerGmTeleportZone(Row.Destination);
            continue;
        }
        FString Error;
        const bool bSuccess = Portal->TryTraverse(Character, Error);
        if (auto* PC = Cast<AWarPlayerController>(Player)) PC->ClientZoneTravelStatus(bSuccess ? FString() : Error);
    }
}
