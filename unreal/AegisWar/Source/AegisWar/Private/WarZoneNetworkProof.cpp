#include "WarZoneNetworkProof.h"
#include "WarZoneStreamingSubsystem.h"
#include "WarZoneAnchor.h"
#include "WarZonePortal.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarZoneLightingSubsystem.h"
#include "Engine/Level.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/NetConnection.h"
#include "Engine/LevelStreaming.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

bool UWarZoneNetworkProof::ShouldCreateSubsystem(UObject* Outer) const
{
    return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer)
        && FParse::Param(FCommandLine::Get(), TEXT("WarZoneNetworkProof"));
}
TStatId UWarZoneNetworkProof::GetStatId() const
{ RETURN_QUICK_DECLARE_CYCLE_STAT(UWarZoneNetworkProof, STATGROUP_Tickables); }
void UWarZoneNetworkProof::Finish(bool bPassed, const FString& Detail)
{
    bFinished = true;
    UE_LOG(LogTemp, Display, TEXT("WAR_ZONE_NETWORK_PROOF passed=%d %s"), bPassed, *Detail);
    FString Run;
    FParse::Value(FCommandLine::Get(), TEXT("WarProofRun="), Run);
    if (Run.IsEmpty() || Run.Contains(TEXT("/")) || Run.Contains(TEXT("\\")) || Run.Contains(TEXT(".."))) return;
    const FString Directory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("ZoneNetworkProof"), Run);
    IFileManager::Get().MakeDirectory(*Directory, true);
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("{\"passed\":%s,\"stage\":%d,\"twoClientStreaming\":%s,\"productionAccepted\":false}"),
        bPassed ? TEXT("true") : TEXT("false"), Stage, bPassed ? TEXT("true") : TEXT("false")), *FPaths::Combine(Directory,TEXT("report.json")));
}
void UWarZoneNetworkProof::Tick(float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    if (GetWorld()->GetNetMode() == NM_Client) { InspectClientResidency(); return; }
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now > Deadline) { Finish(false, FString::Printf(TEXT("Timed out at stage %d"), Stage)); return; }
    if (Now < NextCheck) return;
    NextCheck = Now + 0.1;
    auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
    if (!Streaming) { Finish(false, TEXT("Streaming subsystem missing")); return; }
    if (Stage == 0)
    {
        for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        {
            auto* PC = It->Get();
            const auto* State = PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
            auto* Pawn = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
            if (!State || !Pawn || !Pawn->IsVisualReady() || !PC->GetNetConnection()
                || !Streaming->IsZoneReady(State->GetCurrentZone(), PC)) continue;
            if (State->GetRealm() == EWarRealm::Aegis) Traveler = PC; else Resident = PC;
        }
        if (!Traveler.IsValid() || !Resident.IsValid()) return;
        ResidentPosition = Resident->GetPawn()->GetActorLocation();
        TravelPawn = Cast<AWarCharacter>(Traveler->GetPawn());
        FWarInventoryItem Stack; Stack.Key=TEXT("potion_health"); Stack.Kind=TEXT("consumable"); Stack.Quantity=3;
        FString Error;
        auto* State = Traveler->GetPlayerState<AWarPlayerState>();
        if (!State->GrantRewards(FGuid::NewGuid(), {Stack}, Error)) { Finish(false, Error); return; }
        Revision = State->GetInventory().Revision;
        Stage = 1;
    }
    auto* PC = Traveler.Get(); auto* Other = Resident.Get();
    auto* Pawn = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    const auto* State = PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
    const auto* OtherState = Other ? Other->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!Pawn || Pawn != TravelPawn.Get() || !State || !Other || !Other->GetPawn() || !OtherState
        || OtherState->GetCurrentZone() != TEXT("riftspire_capital")
        || FVector::Dist2D(Other->GetPawn()->GetActorLocation(), ResidentPosition) > 100
        || State->GetInventory().Revision != Revision)
    { Finish(false, FString::Printf(TEXT("Player isolation failed: samePawn=%d otherZone=%s distance=%.1f inventory=%d/%d"),
        Pawn && Pawn == TravelPawn.Get(), OtherState ? *OtherState->GetCurrentZone().ToString() : TEXT("missing"),
        Other && Other->GetPawn() ? FVector::Dist2D(Other->GetPawn()->GetActorLocation(), ResidentPosition) : -1.0,
        State ? State->GetInventory().Revision : -1, Revision)); return; }
    auto* Field = AWarZoneAnchor::FindById(GetWorld(), TEXT("sunmeadow_march"));
    if (!Field || Field->ContentLevels.IsEmpty()) { Finish(false, TEXT("Partitioned Sunmeadow missing")); return; }
    if (Stage == 1 || Stage == 3)
    {
        if (Stage == 3)
        {
            // The server keeps the union of occupied zones. Bastion must cease residency after its travel hold expires.
            for (TActorIterator<AWarZoneAnchor> It(GetWorld()); It; ++It)
                for (FName Package : It->ContentLevels)
                {
                    const auto* Level = UGameplayStatics::GetStreamingLevel(GetWorld(), Package);
                    const bool bServerExpected = It->ZoneId == Field->ZoneId || It->ZoneId == TEXT("riftspire_capital");
                    if (!Level || Level->IsLevelLoaded() != bServerExpected) return;
                    if (PC->GetNetConnection()->ClientVisibleLevelNames.Contains(Package) != (It->ZoneId == Field->ZoneId)
                        || Other->GetNetConnection()->ClientVisibleLevelNames.Contains(Package) != (It->ZoneId == TEXT("riftspire_capital"))) return;
                }
            UE_LOG(LogTemp, Display, TEXT("WAR_VACANT_CAPITAL_UNLOADED_SERVER_AND_CLIENTS"));
        }
        const FName Route = Stage == 1 ? TEXT("aegis_capital_to_sunmeadow_march") : TEXT("sunmeadow_march_to_aegis_capital");
        AWarZonePortal* Portal = nullptr;
        for (TActorIterator<AWarZonePortal> It(GetWorld()); It; ++It) if (It->RouteId == Route) { Portal = *It; break; }
        if (!Portal) { Finish(false, TEXT("Test portal missing")); return; }
        Portal->SetActorEnableCollision(false);
        if (!Pawn->TeleportTo(Portal->GetActorLocation(), Pawn->GetActorRotation())) { Finish(false, TEXT("Portal approach blocked")); return; }
        FString Error;
        const bool bTraversed = Portal->TryTraverse(Pawn, Error);
        Portal->SetActorEnableCollision(true);
        if (!bTraversed && !Streaming->HasPending(Pawn)) { Finish(false, Error); return; }
        ++Stage; Deadline = Now + 45; return;
    }
    if (Stage == 2)
    {
        if (Streaming->HasPending(Pawn)) return;
        if (State->GetCurrentZone() != Field->ZoneId || !Streaming->IsZoneReady(Field->ZoneId, PC))
        { Finish(false, TEXT("Traveler entered before client content readiness")); return; }
        for (FName Package : Field->ContentLevels)
            if (Other->GetNetConnection()->ClientVisibleLevelNames.Contains(Package))
            { Finish(false, TEXT("Unrelated client loaded the traveler's destination")); return; }
        if (!Streaming->IsZoneReady(TEXT("riftspire_capital"), Other))
        { Finish(false, TEXT("Resident's occupied zone was unloaded")); return; }
        Stage = 3; NextCheck = Now + 7; return;
    }
    if (Stage == 4)
    {
        if (Streaming->HasPending(Pawn)) return;
        if (State->GetCurrentZone() != TEXT("aegis_capital")) { Finish(false, TEXT("Return portal failed")); return; }
        for (FName Package : Field->ContentLevels)
        {
            const auto* Level = UGameplayStatics::GetStreamingLevel(GetWorld(), Package);
            if (!Level || Level->IsLevelLoaded() || PC->GetNetConnection()->ClientVisibleLevelNames.Contains(Package)) return;
        }
        if (!Streaming->IsZoneReady(TEXT("riftspire_capital"), Other))
        { Finish(false, TEXT("Resident lost collision after another player's return")); return; }
        Stage = 5;
        Finish(true, TEXT("Only the entering client loaded Sunmeadow; resident, inventory and pawn preserved; vacant zone unloaded"));
    }
}

void UWarZoneNetworkProof::InspectClientResidency()
{
    auto* Player = GetWorld()->GetFirstPlayerController();
    const auto* State = Player ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!State || !Player->GetPawn()) return;
    const FName Zone = State->GetCurrentZone();
    const double Now = GetWorld()->GetTimeSeconds();
    if (Zone != LastClientZone) { LastClientZone = Zone; ClientSettledAt = Now + 1; }
    if (Now < ClientSettledAt) return;
    int32 VisibleContentLevels = 0, ContentActors = 0, PersistentMeshes = 0;
    for (TActorIterator<AWarZoneAnchor> It(GetWorld()); It; ++It)
        for (FName Package : It->ContentLevels)
        {
            const auto* Level = UGameplayStatics::GetStreamingLevel(GetWorld(), Package);
            if (!Level || Level->IsLevelLoaded() != (It->ZoneId == Zone)) return;
            if (Level->IsLevelLoaded())
            {
                if (!Level->IsLevelVisible()) return;
                ++VisibleContentLevels;
                for (AActor* Actor : Level->GetLoadedLevel()->Actors) if (IsValid(Actor)) ++ContentActors;
            }
        }
    for (AActor* Actor : GetWorld()->PersistentLevel->Actors) if (IsValid(Actor) && Actor->IsA<AStaticMeshActor>()) ++PersistentMeshes;
    const auto* Lighting = GetWorld()->GetSubsystem<UWarZoneLightingSubsystem>();
    if (!Lighting || Lighting->GetActiveZone() != Zone) return;
    FString Run; FParse::Value(FCommandLine::Get(), TEXT("WarProofRun="), Run);
    if (Run.IsEmpty() || Run.Contains(TEXT("/")) || Run.Contains(TEXT("\\")) || Run.Contains(TEXT(".."))) return;
    const FString Directory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("ZoneNetworkProof"), Run);
    IFileManager::Get().MakeDirectory(*Directory, true);
    const FString Name = FString::Printf(TEXT("client_%s_%s.json"),
        State->GetRealm() == EWarRealm::Aegis ? TEXT("aegis") : TEXT("rift"), *Zone.ToString());
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("{\"zone\":\"%s\",\"onlyCurrentZoneLoaded\":true,\"contentLevels\":%d,\"contentActors\":%d,\"persistentStaticMeshes\":%d,\"lightingMatchesZone\":true}"),
        *Zone.ToString(), VisibleContentLevels, ContentActors, PersistentMeshes), *FPaths::Combine(Directory, Name));
    ClientSettledAt = Now + 60;
    UE_LOG(LogTemp, Display, TEXT("WAR_CLIENT_ZONE_RESIDENCY zone=%s levels=%d actors=%d persistentMeshes=%d"),
        *Zone.ToString(), VisibleContentLevels, ContentActors, PersistentMeshes);
}
