#include "WarPortalProof.h"
#include "WarZonePortal.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarZoneAnchor.h"
#include "WarZoneStreamingSubsystem.h"
#include "WarResourceNode.h"
#include "WarWorldEditSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"

bool UWarPortalProof::ShouldCreateSubsystem(UObject* Outer) const
{
    return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer)
        && FParse::Param(FCommandLine::Get(), TEXT("WarPortalProof"));
}
TStatId UWarPortalProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarPortalProof, STATGROUP_Tickables); }
void UWarPortalProof::Finish(bool bPassed, const FString& Detail)
{
    bFinished = true;
    UE_LOG(LogTemp, Display, TEXT("WAR_PORTAL_PROOF passed=%d %s"), bPassed, *Detail);
    const FString Directory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("PortalProof"));
    IFileManager::Get().MakeDirectory(*Directory, true);
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("{\"passed\":%s,\"routesTraversed\":%d,\"resourcesGathered\":%d,\"deferredRoutes\":%d,\"streamingChecks\":%d,\"gmDraftAndHistory\":%s,\"fullInventory\":%s,\"networkAccepted\":false,\"visualApproved\":false}"),
        bPassed ? TEXT("true") : TEXT("false"), Step, ResourcesGathered, DeferredRoutes, StreamingChecks,
        bGmVerified ? TEXT("true") : TEXT("false"), bFullInventoryVerified ? TEXT("true") : TEXT("false")), *FPaths::Combine(Directory, TEXT("report.json")));
    FPlatformMisc::RequestExitWithStatus(false, bPassed ? 0 : 1);
}
void UWarPortalProof::Tick(float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now < NextStep) return;
    auto* PC = GetWorld()->GetFirstPlayerController();
    auto* Character = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    auto* State = PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!Character || !State || !Character->IsVisualReady())
    { if (Now > 90) Finish(false, TEXT("Player did not initialize")); return; }
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    if (GmObjectId.IsNone())
    {
        FString Error;
        if (!Editor || !Editor->Open(PC, Error) || Editor->GetHistory().GetObjects().IsEmpty()
            || !Editor->GetDraftLocation().Contains(TEXT("WorldEditPortalProof")))
        { Finish(false, TEXT("Isolated GM travel fixture unavailable: ") + Error); return; }
        const auto Original = Editor->GetHistory().GetObjects()[0];
        GmObjectId = Original.Id; GmOriginalHidden = Original.bHidden;
        if (!Editor->Edit(PC, Original.Id, Original.Transform, !Original.bHidden, Editor->GetHistory().GetRevision(), Error)
            || !Editor->SaveDraft(PC, Editor->GetHistory().GetRevision(), Error))
        { Finish(false, TEXT("Could not save isolated GM travel draft: ") + Error); return; }
        GmSnapshot = Editor->GetHistory().ExportDraft();
    }
    TArray<FName> Routes;
    for (TActorIterator<AWarZonePortal> It(GetWorld()); It; ++It) if (It->bDestinationBuilt) Routes.Add(It->RouteId);
    Routes.Sort(FNameLexicalLess());
    int32 Expected = 70;
    FParse::Value(FCommandLine::Get(),TEXT("WarPortalProofRoutes="),Expected);
    if (Routes.Num()!=Expected) { Finish(false,TEXT("Unexpected directed route count")); return; }
    auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
    if (!bGmUnloadedVerified && Streaming && State->GetCurrentZone() != TEXT("aegis_capital")
        && !Streaming->IsZoneReady(TEXT("aegis_capital")))
    {
        if (Editor->GetObjectActor(GmObjectId) || Editor->GetHistory().ExportDraft() != GmSnapshot)
        { Finish(false, TEXT("Capital unload retained a GM actor or changed its draft")); return; }
        bGmUnloadedVerified = true;
        UE_LOG(LogTemp, Display, TEXT("WAR_GM_CAPITAL_UNLOADED_HISTORY_PASSED"));
    }
    if (Streaming && StreamingChecks < 2)
    {
        AWarZonePortal* Portal = nullptr;
        for (TActorIterator<AWarZonePortal> It(GetWorld()); It; ++It)
            if (It->RouteId == TEXT("aegis_capital_to_aegis_gate_fortress")) { Portal = *It; break; }
        auto* Target = Portal ? AWarZoneAnchor::FindAt(GetWorld(), Portal->ArrivalLocation) : nullptr;
        if (!Portal || !Target || Target->ContentLevels.IsEmpty()) StreamingChecks = 2; // Legacy all-loaded map.
        else if (StreamingChecks == 0)
        {
            OriginalPosition = Character->GetActorLocation();
            Portal->SetActorEnableCollision(false);
            if (!Character->TeleportTo(Portal->GetActorLocation(), Character->GetActorRotation()))
            { Finish(false, TEXT("Streaming check approach blocked")); return; }
            const FVector Waiting = Character->GetActorLocation();
            const FName ZoneBefore = State->GetCurrentZone();
            const auto Packages = Target->ContentLevels;
            Target->ContentLevels = {TEXT("/Game/WorldRebuild/MissingProofDestination")};
            FString Error;
            const bool bRejected = !Portal->TryTraverse(Character, Error) && !Streaming->HasPending(Character)
                && Character->GetActorLocation().Equals(Waiting) && State->GetCurrentZone() == ZoneBefore;
            Target->ContentLevels = Packages;
            if (!bRejected) { Finish(false, TEXT("Missing destination did not fail safely")); return; }
            Portal->TryTraverse(Character, Error);
            if (!Streaming->HasPending(Character) || !Character->GetActorLocation().Equals(Waiting))
            { Finish(false, TEXT("Expected deferred travel without moving the pawn")); return; }
            if (!Character->TeleportTo(OriginalPosition, Character->GetActorRotation()))
            { Finish(false, TEXT("Could not leave portal for cancellation proof")); return; }
            Portal->SetActorEnableCollision(true);
            StreamingChecks = 1; NextStep = Now + 0.3; return;
        }
        else
        {
            if (Streaming->HasPending(Character) || FVector::Dist2D(Character->GetActorLocation(), OriginalPosition) > 100)
            { Finish(false, TEXT("Walking away did not cancel portal loading")); return; }
            StreamingChecks = 2;
            UE_LOG(LogTemp, Display, TEXT("WAR_STREAMING_FAILURE_AND_CANCEL_PASSED"));
        }
    }
    if (!bResourcesVerified)
    {
        FString LoadError;
        bool bReady = true;
        for (const FName Zone : {FName(TEXT("riftspire_capital")), FName(TEXT("sunmeadow_march")), FName(TEXT("cinderfen_outskirts"))})
        {
            if (Streaming && !Streaming->EnsureZone(Zone, LoadError))
            { Finish(false, TEXT("Resource zone load failed: ") + LoadError); return; }
            bReady &= !Streaming || Streaming->IsZoneReady(Zone);
        }
        if (!bReady)
        {
            if (LoadDeadline == 0) LoadDeadline = Now + 90;
            if (Now > LoadDeadline) Finish(false, TEXT("Resource zone loading timed out"));
            return;
        }
        LoadDeadline = 0;
        FWarInventoryItem Stack; Stack.Key=TEXT("potion_health"); Stack.Kind=TEXT("consumable"); Stack.Quantity=3;
        FString Error;
        if (!State->GrantRewards(FGuid::NewGuid(), {Stack}, Error))
        { Finish(false, TEXT("Could not initialize inventory proof: ") + Error); return; }
        TArray<AWarResourceNode*> Nodes;
        for (TActorIterator<AWarResourceNode> It(GetWorld()); It; ++It) Nodes.Add(*It);
        Nodes.Sort([](const AWarResourceNode& A, const AWarResourceNode& B) {
            if ((A.ZoneId == TEXT("sunmeadow_march")) != (B.ZoneId == TEXT("sunmeadow_march")))
                return A.ZoneId == TEXT("sunmeadow_march");
            return A.NodeId.LexicalLess(B.NodeId);
        });
        for (auto* It : Nodes)
        {
            FWarResourceDefinition Definition;
            bool bReached=false;
            for (int32 Direction=0; Direction<8 && !bReached; ++Direction)
            {
                const double Angle=Direction*PI/4;
                const FVector Offset(200*FMath::Cos(Angle),200*FMath::Sin(Angle),Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+5);
                bReached=Character->TeleportTo(It->GetActorLocation()+Offset,Character->GetActorRotation())
                    && It->ResolveInteraction(Character,Definition,Error);
            }
            if (!bReached) { Finish(false,TEXT("Resource approach failed: ")+It->NodeId.ToString()+TEXT(" ")+Error); return; }
            if (!bFullInventoryVerified)
            {
                if (State->GetInventory().Items.Num()!=1) { Finish(false,TEXT("Unexpected inventory fixture")); return; }
                TArray<FWarInventoryItem> Fill;
                for (int32 Slot=1; Slot<WarInventory::Capacity; ++Slot)
                {
                    FWarInventoryItem Item; Item.Key=FName(*FString::Printf(TEXT("portal_proof_fill_%d"),Slot));
                    Item.Kind=TEXT("misc"); Item.Quantity=99; Fill.Add(Item);
                }
                if (!State->GrantRewards(FGuid::NewGuid(),Fill,Error) || State->GetInventory().Items.Num()!=WarInventory::Capacity)
                { Finish(false,TEXT("Could not fill resource proof inventory: ")+Error); return; }
                const auto Full = State->GetInventory();
                if (State->GatherResource(It,Full.Revision,Error) || !Error.Contains(TEXT("Inventory full"))
                    || !FWarInventorySnapshot::StaticStruct()->CompareScriptStruct(&Full,&State->GetInventory(),0))
                { Finish(false,TEXT("Full inventory gathering was not atomic: ")+Error); return; }
                TMap<int32,int32> Remove;
                for (const auto& Item : Full.Items)
                    if (Item.Key.ToString().StartsWith(TEXT("portal_proof_fill_"))) Remove.Add(Item.Slot,Item.Quantity);
                if (!State->ExchangeItems(FGuid::NewGuid(),Full.Revision,Remove,{},Error))
                { Finish(false,TEXT("Could not restore resource proof inventory: ")+Error); return; }
                bFullInventoryVerified=true;
                UE_LOG(LogTemp,Display,TEXT("WAR_FULL_INVENTORY_RESOURCE_PASSED=%s"),*It->NodeId.ToString());
            }
            const auto BeforeSnapshot=State->GetInventory();
            const int32 Before=BeforeSnapshot.Revision;
            if (State->GatherResource(It,Before-1,Error)
                || !FWarInventorySnapshot::StaticStruct()->CompareScriptStruct(&BeforeSnapshot,&State->GetInventory(),0))
            { Finish(false,TEXT("Stale gathering request changed inventory")); return; }
            if (!State->GatherResource(It,Before,Error) || State->GetInventory().Revision!=Before+1)
            { Finish(false,TEXT("Source gathering failed: ")+It->NodeId.ToString()+TEXT(" ")+Error); return; }
            const auto* Cooldown=State->GetInventory().ResourceCooldowns.FindByPredicate([&](const FWarResourceCooldown& Row) {
                return Row.ZoneId==It->ZoneId && Row.NodeId==It->NodeId;
            });
            if (!Cooldown || State->GatherResource(It,Before+1,Error) || State->GetInventory().Revision!=Before+1)
            { Finish(false,TEXT("Gather cooldown failed: ")+It->NodeId.ToString()); return; }
            ++ResourcesGathered;
            UE_LOG(LogTemp,Display,TEXT("WAR_WORLD_RESOURCE_PASSED=%s"),*It->NodeId.ToString());
        }
        if (ResourcesGathered!=20) { Finish(false,TEXT("Expected fourteen capital and six frontier resource nodes")); return; }
        bResourcesVerified = true;
    }
    const auto* Stack = State->GetInventory().Items.FindByPredicate([](const FWarInventoryItem& Item) {
        return Item.Key==TEXT("potion_health") && Item.Kind==TEXT("consumable") && Item.Quantity==3;
    });
    if (!Stack) { Finish(false,TEXT("Inventory stack did not survive travel or respawn")); return; }
    if (ActivePortal.IsValid())
    {
        auto* Portal = ActivePortal.Get();
        if (Streaming && Streaming->HasPending(Character))
        {
            if (Now > TravelDeadline) Finish(false, TEXT("Deferred traversal timed out"));
            return;
        }
        if (FVector::Dist2D(Character->GetActorLocation(), Portal->ArrivalLocation) > 200
            || TravelPawn.Get() != Character || State->GetInventory().Revision != TravelRevision)
        { Finish(false, TEXT("Traversal failed: ") + Portal->RouteId.ToString()); return; }
        const auto* Zone = AWarZoneAnchor::FindAt(GetWorld(), Character->GetActorLocation());
        if (!Zone || Zone->ZoneId != State->GetCurrentZone())
        { Finish(false, TEXT("Zone state did not follow travel")); return; }
        UE_LOG(LogTemp, Display, TEXT("WAR_PORTAL_ROUTE_PASSED=%s"), *Portal->RouteId.ToString());
        ActivePortal.Reset(); ++Step; NextStep = Now + 3.2; return;
    }
    if (Step == Routes.Num())
    {
        if (RespawnRevision==INDEX_NONE)
        {
            RespawnPawn=Character; RespawnZone=State->GetCurrentZone(); RespawnRevision=State->GetInventory().Revision;
            Character->HandleDeath(); NextStep=Now+6; return;
        }
        const auto* Zone=AWarZoneAnchor::FindAt(GetWorld(),Character->GetActorLocation());
        if (!bGmUnloadedVerified) { Finish(false, TEXT("Capital was never observed unloaded")); return; }
        // Proof-only residency hold reloads the original capital objects without moving the respawned pawn.
        if (Streaming && !Streaming->IsZoneReady(TEXT("aegis_capital")))
        {
            FString Error;
            if (LoadDeadline == 0) LoadDeadline = Now + 45;
            if (!Streaming->EnsureZone(TEXT("aegis_capital"), Error) || Now > LoadDeadline)
                Finish(false, TEXT("Capital draft reload failed: ") + Error);
            return;
        }
        FString GmError;
        const auto GmHidden = [Editor, this]() {
            const auto* Object = Editor ? Editor->GetHistory().Find(GmObjectId) : nullptr;
            const auto* Actor = Editor ? Editor->GetObjectActor(GmObjectId) : nullptr;
            return Object && Actor && Object->bHidden == Actor->IsHidden() && Object->bHidden != GmOriginalHidden;
        };
        if (!Editor || Editor->GetHistory().ExportDraft() != GmSnapshot || !GmHidden()
            || !Editor->Undo(PC, false, Editor->GetHistory().GetRevision(), GmError) || GmHidden()
            || !Editor->Undo(PC, true, Editor->GetHistory().GetRevision(), GmError) || !GmHidden()
            || !Editor->Undo(PC, false, Editor->GetHistory().GetRevision(), GmError)
            || !Editor->LoadDraft(PC, Editor->GetHistory().GetRevision(), GmError) || !GmHidden()
            || !Editor->Undo(PC, false, Editor->GetHistory().GetRevision(), GmError) || GmHidden())
        { Finish(false, TEXT("GM draft/history did not survive zone streaming and respawn: ") + GmError); return; }
        bGmVerified = true;
        UE_LOG(LogTemp, Display, TEXT("WAR_GM_TRAVEL_HISTORY_PASSED"));
        Finish(RespawnPawn.Get()!=Character && Zone && Zone->ZoneId==RespawnZone && State->GetInventory().Revision==RespawnRevision,
            FString::Printf(TEXT("Respawn: replaced=%d expectedZone=%s actualZone=%s inventory=%d/%d"),
                RespawnPawn.Get()!=Character, *RespawnZone.ToString(), Zone ? *Zone->ZoneId.ToString() : TEXT("none"),
                State->GetInventory().Revision, RespawnRevision)); return;
    }
    AWarZonePortal* Portal = nullptr;
    for (TActorIterator<AWarZonePortal> It(GetWorld()); It; ++It) if (It->RouteId == Routes[Step]) Portal = *It;
    if (!Portal) { Finish(false, TEXT("Portal missing")); return; }
    const auto* SourceZone = AWarZoneAnchor::FindAt(GetWorld(), Portal->GetActorLocation());
    if (!SourceZone) { Finish(false, TEXT("Source anchor missing")); return; }
    FString LoadError;
    if (Streaming && !Streaming->IsZoneReady(SourceZone->ZoneId))
    {
        if (LoadDeadline == 0) LoadDeadline = Now + 90;
        if (!Streaming->EnsureZone(SourceZone->ZoneId, LoadError) || Now > LoadDeadline)
            Finish(false, TEXT("Source zone load failed: ") + LoadError);
        return;
    }
    LoadDeadline = 0;
    const int32 Revision = State->GetInventory().Revision;
    // Position at the actual trigger without letting the overlap callback race the explicit assertion.
    Portal->SetActorEnableCollision(false);
    if (!Character->TeleportTo(Portal->GetActorLocation(), Character->GetActorRotation()))
    { Finish(false, TEXT("Portal approach is obstructed")); return; }
    FString Error;
    bool bTraversed;
    if (Step % 2 == 0)
    {
        bTraversed = Portal->TryTraverse(Character, Error);
        Portal->SetActorEnableCollision(true);
    }
    else
    {
        // Restoring the trigger around the player must use the real overlap entry point.
        Portal->SetActorEnableCollision(true);
        bTraversed = FVector::Dist2D(Character->GetActorLocation(), Portal->ArrivalLocation) <= 200;
    }
    const bool bPending = Streaming && Streaming->HasPending(Character);
    if (!bTraversed && !bPending)
    { Finish(false, TEXT("Traversal failed: ") + Portal->RouteId.ToString() + TEXT(" ") + Error); return; }
    if (bPending) ++DeferredRoutes;
    ActivePortal = Portal; TravelPawn = Character; TravelRevision = Revision; TravelDeadline = Now + 35;
}
