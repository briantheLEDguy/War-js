#include "WarZoneStreamingSubsystem.h"
#include "WarZoneAnchor.h"
#include "WarCityDefinition.h"
#include "WarZonePortal.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarCityNpc.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarGameMode.h"
#include "WarSiegeEncounter.h"
#include "WarCampaignSiegeSubsystem.h"
#include "Engine/LevelStreaming.h"
#include "Engine/Level.h"
#include "Engine/Brush.h"
#include "Engine/LevelStreamingVolume.h"
#include "Components/PrimitiveComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/NetConnection.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

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
    FString CityError;
    if (!Anchor->ValidateCity(CityError)) return Waiting(CityError);
    for (const FName Package : Anchor->GetContentLevels())
    {
        const auto* Level = UGameplayStatics::GetStreamingLevel(GetWorld(), Package);
        if (!Level || !Level->IsLevelLoaded() || !Level->IsLevelVisible())
            return Waiting(FString::Printf(TEXT("Level is not visible: %s"), *Package.ToString()));
        if (Anchor->CityDefinition && Anchor->CityDefinition->Packages().Contains(Package)
            && !UWarCityDefinition::ValidateLevel(Level->GetLoadedLevel(), CityError)) return Waiting(CityError);
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
    if (!Anchor->GetContentLevels().IsEmpty())
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
    if (!Anchor->ValidateCity(Error)) return false;
    for (FName Package : Anchor->GetContentLevels())
        if (!UGameplayStatics::GetStreamingLevel(GetWorld(), Package))
        { Error = TEXT("Destination content is unavailable. You remain in the current zone."); return false; }
    KeepUntil.Add(Zone, GetWorld()->GetTimeSeconds() + 5.0);
    for (FName Package : Anchor->GetContentLevels())
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
    if (const auto* State = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
        State && State->IsScenarioTransferPending())
    { Error = TEXT("Scenario departure is in progress."); return false; }
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
    FName Destination, FString& Error, bool Evacuation)
{
    auto* Player = Character ? Cast<APlayerController>(Character->GetController()) : nullptr;
    if (!Portal || !Player || !EnsureZone(Destination, Error)) return false;
    const auto* Existing = Pending.FindByPredicate([Character](const FPending& Row) { return Row.Character.Get() == Character; });
    if (Existing)
    {
        Error = Existing->Portal.Get() == Portal ? TEXT("Loading destination. Move away to cancel.") : TEXT("Another portal is loading. Move away to cancel.");
        return false;
    }
    Pending.Add({Portal, Character, Player, Destination, GetWorld()->GetTimeSeconds() + 30.0, false, FVector::ZeroVector, Evacuation});
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
    for (auto It = ZonePins.CreateIterator(); It; ++It)
        if (!It.Key().IsValid()) It.RemoveCurrent(); else WantedZones.Add(It.Value());
    for (auto It = KeepUntil.CreateIterator(); It; ++It)
        if (It.Value() <= Now) It.RemoveCurrent(); else WantedZones.Add(It.Key());
    TMap<TWeakObjectPtr<APlayerController>, TSet<FName>> PlayerZones;
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        auto* Player = It->Get();
        if (!Player) continue;
        auto& Zones = PlayerZones.FindOrAdd(Player);
        if (const auto* State = Player->GetPlayerState<AWarPlayerState>())
        { Zones.Add(State->GetCurrentZone()); if (const auto* Siege = State->GetSiegeEncounter(); Siege && Siege->bCampaign) Zones.Add(TEXT("aegis_capital")); }
        if (const APawn* Pawn = Player->GetPawn())
            if (const auto* Anchor = AWarZoneAnchor::FindAt(GetWorld(), Pawn->GetActorLocation())) Zones.Add(Anchor->ZoneId);
        for (const auto& Row : Pending) if (Row.Player.Get() == Player) Zones.Add(Row.Destination);
        WantedZones.Append(Zones);
    }
    TSet<FName> WantedPackages;
    TSet<FName> ManagedPackages;
    for (TActorIterator<AWarZoneAnchor> It(GetWorld()); It; ++It)
    {
        for (FName Package : It->GetContentLevels())
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
        // Connectionless authority controllers execute client RPCs locally, which
        // would replace the server's union with one player's streaming subset.
        if (!Player || Player->IsLocalController() || !Player->GetNetConnection()) continue;
        TSet<FName> Wanted;
        for (FName Zone : Entry.Value)
            if (const auto* Anchor = AWarZoneAnchor::FindById(GetWorld(), Zone)) Wanted.Append(Anchor->GetContentLevels());
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

FString UWarZoneStreamingSubsystem::DescribeZoneStreaming(FName Zone) const
{
    const auto* World = GetWorld();
    const double Now = World->GetTimeSeconds();
    auto Snapshot = MakeShared<FJsonObject>();
    Snapshot->SetNumberField(TEXT("schemaVersion"), 1);
    Snapshot->SetBoolField(TEXT("diagnosticOnly"), true);
    Snapshot->SetStringField(TEXT("zone"), Zone.ToString());
    Snapshot->SetBoolField(TEXT("levelLoadRequestsAllowed"), World->AllowLevelLoadRequests());
    TSet<TWeakObjectPtr<APlayerController>> WorldPlayers;
    for (auto It = World->GetPlayerControllerIterator(); It; ++It)
        if (auto* Player = It->Get()) WorldPlayers.Add(Player);
    Snapshot->SetNumberField(TEXT("worldControllers"), WorldPlayers.Num());
    Snapshot->SetNumberField(TEXT("pendingRequestsTotal"), Pending.Num());
    Snapshot->SetNumberField(TEXT("clientPackageOwners"), ClientPackages.Num());
    int32 Pins = 0;
    for (const auto& Pin : ZonePins) if (Pin.Key.IsValid() && Pin.Value == Zone) ++Pins;
    Snapshot->SetNumberField(TEXT("zonePins"), Pins);
    Snapshot->SetNumberField(TEXT("graceSecondsRemaining"), FMath::Max(0.0, KeepUntil.FindRef(Zone) - Now));
    TArray<TSharedPtr<FJsonValue>> Requests;
    int32 RequestCount = 0, OwnersInWorld = 0;
    for (const auto& Request : Pending)
    {
        if (Request.Destination != Zone) continue;
        ++RequestCount;
        const auto* Player = Request.Player.Get();
        OwnersInWorld += WorldPlayers.Contains(Request.Player);
        if (Requests.Num() >= 64) continue;
        auto Row = MakeShared<FJsonObject>();
        const auto* State = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
        const APawn* Pawn = Player ? Player->GetPawn() : nullptr;
        const auto* Source = Pawn ? AWarZoneAnchor::FindAt(GetWorld(), Pawn->GetActorLocation()) : nullptr;
        Row->SetBoolField(TEXT("ownerInWorld"), WorldPlayers.Contains(Request.Player));
        Row->SetBoolField(TEXT("ownerValid"), Player != nullptr);
        Row->SetBoolField(TEXT("networkConnection"), Player && Player->GetNetConnection());
        Row->SetBoolField(TEXT("localController"), Player && Player->IsLocalController());
        Row->SetBoolField(TEXT("samePawn"), Pawn && Pawn == Request.Character.Get());
        Row->SetBoolField(TEXT("evacuation"), Request.bEvacuation);
        Row->SetStringField(TEXT("currentZone"), State ? State->GetCurrentZone().ToString() : FString());
        Row->SetStringField(TEXT("physicalZone"), Source ? Source->ZoneId.ToString() : FString());
        Row->SetNumberField(TEXT("deadlineSecondsRemaining"), Request.Deadline - Now);
        Requests.Add(MakeShared<FJsonValueObject>(Row));
    }
    Snapshot->SetNumberField(TEXT("pendingRequestsForZone"), RequestCount);
    Snapshot->SetNumberField(TEXT("pendingOwnersInWorld"), OwnersInWorld);
    Snapshot->SetBoolField(TEXT("requestsTruncated"), RequestCount > Requests.Num());
    Snapshot->SetArrayField(TEXT("requests"), Requests);
    const auto* Anchor = AWarZoneAnchor::FindById(GetWorld(), Zone);
    Snapshot->SetBoolField(TEXT("uniqueAnchor"), Anchor != nullptr);
    const TArray<FName> Packages = Anchor ? Anchor->GetContentLevels() : TArray<FName>();
    Snapshot->SetNumberField(TEXT("contentLevels"), Packages.Num());
    Snapshot->SetBoolField(TEXT("levelsTruncated"), Packages.Num() > 32);
    TArray<TSharedPtr<FJsonValue>> Levels;
    for (int32 Index = 0; Index < FMath::Min(Packages.Num(), 32); ++Index)
    {
        const FName Package = Packages[Index];
        const auto* Stream = UGameplayStatics::GetStreamingLevel(GetWorld(), Package);
        auto Row = MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("package"), Package.ToString());
        Row->SetBoolField(TEXT("declared"), Stream != nullptr);
        int32 Declarations = 0;
        for (const ULevelStreaming* Candidate : World->GetStreamingLevels())
            if (Candidate && Candidate->GetWorldAssetPackageFName() == Package) ++Declarations;
        Row->SetNumberField(TEXT("matchingDeclarations"), Declarations);
        if (Stream)
        {
            Row->SetStringField(TEXT("class"), Stream->GetClass()->GetName());
            Row->SetBoolField(TEXT("shouldLoad"), Stream->ShouldBeLoaded());
            Row->SetBoolField(TEXT("shouldBeVisible"), Stream->GetShouldBeVisibleFlag());
            Row->SetBoolField(TEXT("loaded"), Stream->IsLevelLoaded());
            Row->SetBoolField(TEXT("visible"), Stream->IsLevelVisible());
            Row->SetStringField(TEXT("state"), EnumToString(Stream->GetLevelStreamingState()));
            Row->SetBoolField(TEXT("loadRequestPending"), Stream->HasLoadRequestPending());
            Row->SetBoolField(TEXT("streamingStatePending"), Stream->IsStreamingStatePending());
            Row->SetBoolField(TEXT("unloadAndRemoval"), Stream->GetIsRequestingUnloadAndRemoval());
            Row->SetNumberField(TEXT("loadedActors"), Stream->GetLoadedLevel() ? Stream->GetLoadedLevel()->Actors.Num() : 0);
            int32 ActiveVolumes = 0;
            for (const ALevelStreamingVolume* Volume : Stream->EditorStreamingVolumes)
                if (IsValid(Volume) && !Volume->bDisabled && !Volume->bEditorPreVisOnly) ++ActiveVolumes;
            Row->SetNumberField(TEXT("activeStreamingVolumes"), ActiveVolumes);
        }
        Levels.Add(MakeShared<FJsonValueObject>(Row));
    }
    Snapshot->SetArrayField(TEXT("levels"), Levels);
    FString Text;
    FJsonSerializer::Serialize(Snapshot, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
    return Text;
}

void UWarZoneStreamingSubsystem::LogRecoveryStreamingDiagnostics()
{
    const double Now = GetWorld()->GetTimeSeconds();
    if (UE_BUILD_SHIPPING || Pending.IsEmpty() || StreamingDiagnosticSamples >= 12 || Now < NextStreamingDiagnosticAt
        || !FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentNetworking"))
        || !FParse::Param(FCommandLine::Get(), TEXT("WarCitadelSiegeProof"))
        || !FParse::Param(FCommandLine::Get(), TEXT("WarCitadelSiegeRecoveryProof"))) return;
    // Capture actual requests without loading content, changing readiness, or extending deadlines.
    NextStreamingDiagnosticAt = Now + 10;
    ++StreamingDiagnosticSamples;
    TSet<FName> Destinations;
    for (const auto& Request : Pending) Destinations.Add(Request.Destination);
    TArray<FName> Zones = Destinations.Array();
    Zones.Sort(FNameLexicalLess());
    for (int32 Index = 0; Index < FMath::Min(Zones.Num(), 8); ++Index)
        UE_LOG(LogTemp, Display, TEXT("WAR_RECOVERY_ZONE_STREAMING sample=%d zonesTruncated=%d %s"),
            StreamingDiagnosticSamples, Zones.Num() > 8, *DescribeZoneStreaming(Zones[Index]));
}

void UWarZoneStreamingSubsystem::Tick(float DeltaTime)
{
    const auto* Mode = GetWorld()->GetAuthGameMode<AWarGameMode>();
    if (!GetWorld()->HasBegunPlay() || !Mode || !Mode->IsDevelopmentSession()) return;
    if (GetWorld()->GetTimeSeconds() < NextUpdateAt) return;
    NextUpdateAt = GetWorld()->GetTimeSeconds() + 0.1;
    UpdateStreaming();
    LogRecoveryStreamingDiagnostics();
    for (int32 Index = Pending.Num() - 1; Index >= 0; --Index)
    {
        const FPending Row = Pending[Index];
        auto* Portal = Row.Portal.Get(); auto* Character = Row.Character.Get(); auto* Player = Row.Player.Get();
        auto* GmPlayer = Row.bGm ? Cast<AWarPlayerController>(Player) : nullptr;
        const auto* State = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
        const auto* Siege = AWarSiegeEncounter::For(Character);
        const auto* Bridge = GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>();
        const bool TrustedEvacuation = Row.bEvacuation && Siege && State && Siege->BlocksCapitalEntry(State) && Siege->CanEvacuate(State->GetRealm(), Row.Destination)
            && Bridge && Bridge->HasEvacuationCheckpoint(Cast<AWarPlayerController>(Player));
        const bool bValidRequest = (!Row.bEvacuation || TrustedEvacuation) && (!(State && State->IsScenarioTransferPending()) || TrustedEvacuation)
            && (Row.bGm ? GmPlayer && GmPlayer->CanUseGmTools() : Portal != nullptr);
        const FVector Source = Row.bGm ? Row.SourcePosition : Portal ? Portal->GetActorLocation() : FVector::ZeroVector;
        const double Radius = Row.bGm ? 250.0 : Portal ? Portal->Radius * Portal->GetActorScale3D().GetAbsMax() : 0.0;
        if (!bValidRequest || !Character || !Player || !CanContinue(Player->GetPawn() == Character,
            !Character->IsDead(), Character->IsVisualReady(), TrustedEvacuation ? 0. : FVector::Dist(Character->GetActorLocation(), Source),
            Radius, GetWorld()->GetTimeSeconds(), Row.Deadline))
        {
            Pending.RemoveAt(Index);
            FString Status = TEXT("Portal loading cancelled. Move into the portal to retry.");
            if (bValidRequest && Character && Player && GetWorld()->GetTimeSeconds() >= Row.Deadline)
            {
                FString Reason;
                IsZoneReady(Row.Destination, Player, &Reason);
                Status = TEXT("Portal loading timed out. Use Interact to retry. ") + Reason;
                UE_LOG(LogTemp, Warning, TEXT("Portal destination %s timed out: %s"), *Row.Destination.ToString(), *Reason);
            }
            if (auto* PC = Cast<AWarPlayerController>(Player)) PC->ClientZoneTravelStatus(Status);
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
        const bool bSuccess = Portal->TryTraverse(Character, Error, TrustedEvacuation);
        if (auto* PC = Cast<AWarPlayerController>(Player)) PC->ClientZoneTravelStatus(bSuccess ? FString() : Error);
    }
}

void UWarZoneStreamingSubsystem::PinZone(AActor* Owner, FName Zone)
{ if (Owner && Owner->HasAuthority() && !Zone.IsNone()) { ZonePins.Add(Owner, Zone); UpdateStreaming(); } }
void UWarZoneStreamingSubsystem::PinZone(UWorldSubsystem* Owner, FName Zone)
{
    if (Owner && Owner->GetWorld()==GetWorld() && GetWorld()->GetNetMode()!=NM_Client
        && !Zone.IsNone() && AWarZoneAnchor::FindById(GetWorld(),Zone))
    { ZonePins.Add(Owner,Zone); UpdateStreaming(); }
}
void UWarZoneStreamingSubsystem::ReleaseZone(UObject* Owner)
{ ZonePins.Remove(Owner); UpdateStreaming(); }
