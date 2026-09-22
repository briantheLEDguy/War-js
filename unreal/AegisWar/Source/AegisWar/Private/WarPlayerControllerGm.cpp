#include "WarPlayerController.h"
#include "WarAbilityRuntime.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarWorldEditSubsystem.h"
#include "WarZonePortal.h"
#include "WarZoneAnchor.h"
#include "WarZoneStreamingSubsystem.h"
#include "WarGmRules.h"
#include "AbilitySystemComponent.h"
#include "GameplayEffect.h"
#include "EngineUtils.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerStart.h"
#include "HAL/PlatformApplicationMisc.h"
#include "NativeGameplayTags.h"

namespace
{
    bool Authorized(AWarPlayerController* PC, FString& Error)
    {
        const auto* Editor = PC && PC->GetWorld() ? PC->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>() : nullptr;
        if (!PC || !PC->HasAuthority() || !Editor || !Editor->CanUse(PC))
        { Error = TEXT("GM access requires an authorized development session. Remote and production privileges are not enabled."); return false; }
        return true;
    }
    bool Land(AWarPlayerController* PC, FVector Position, FString& Error)
    {
        auto* GmPawn = Cast<AWarCharacter>(PC->GetPawn());
        if (!GmPawn || GmPawn->IsDead() || Position.ContainsNaN()) { Error=TEXT("Character or destination unavailable."); return false; }
        FCollisionQueryParams Query(SCENE_QUERY_STAT(GmLanding), false, GmPawn);
        FHitResult Ground;
        if (!PC->GetWorld()->LineTraceSingleByChannel(Ground, Position+FVector(0,0,5000), Position-FVector(0,0,5000), ECC_WorldStatic,Query)
            || !WarGmRules::IsSafeLandingNormal(Ground.ImpactNormal))
        { Error=TEXT("Destination has no safe loaded ground. Teleport was not performed."); return false; }
        const FVector Landing = Ground.ImpactPoint+FVector(0,0,GmPawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+5);
        // Flight normally ignores collision; GM landing still requires a clear capsule.
        if (PC->GetWorld()->OverlapBlockingTestByProfile(Landing,FQuat::Identity,TEXT("Pawn"),
            FCollisionShape::MakeCapsule(GmPawn->GetCapsuleComponent()->GetScaledCapsuleRadius(),GmPawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),Query)
            || !GmPawn->TeleportTo(Landing,GmPawn->GetActorRotation()))
        { Error=TEXT("Destination is obstructed. Teleport was not performed."); return false; }
        GmPawn->GetCharacterMovement()->StopMovementImmediately();
        if (const auto* Anchor = AWarZoneAnchor::FindAt(PC->GetWorld(), GmPawn->GetActorLocation()))
            if (auto* State = PC->GetPlayerState<AWarPlayerState>()) State->SetCurrentZoneTrusted(Anchor->ZoneId);
        if (GmPawn->IsAutoRunning()) GmPawn->ToggleAutoRun();
        GmPawn->ForceNetUpdate(); return true;
    }
}

bool AWarPlayerController::CanUseGmTools() const
{
    const auto* Editor = GetWorld() ? GetWorld()->GetSubsystem<UWarWorldEditSubsystem>() : nullptr;
    return Editor && Editor->CanUse(this);
}
void AWarPlayerController::ToggleGmTools() { ShowInterface(TEXT("GM Tools")); }
void AWarPlayerController::CopyGmCoordinates()
{
    if (!CanUseGmTools() || !GetPawn()) return;
    const FVector P = GetPawn()->GetActorLocation()/100;
    const FString Value = FString::Printf(TEXT("%s | Unreal metres: X %.2f Y %.2f Z %.2f"), *GetWorld()->GetOutermost()->GetName(),P.X,P.Y,P.Z);
    FPlatformApplicationMisc::ClipboardCopy(*Value);
    WorldEditMessage = TEXT("Copied ") + Value;
}
void AWarPlayerController::ServerGmRestore_Implementation()
{
    FString Error;
    if (!Authorized(this,Error)) { ClientWorldEditResult(Error); return; }
    auto* State = GetPlayerState<AWarPlayerState>();
    auto* GmPawn = Cast<AWarCharacter>(GetPawn());
    auto* ASC = State ? State->GetAbilitySystemComponent() : nullptr;
    const auto* Attributes = State ? State->GetAttributes() : nullptr;
    if (!ASC || !Attributes || !GmPawn || GmPawn->IsDead()) { ClientWorldEditResult(TEXT("Wait for the character to finish respawning.")); return; }
    ASC->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),Attributes->GetMaxHealth());
    ASC->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),Attributes->GetMaxMana());
    State->GetClassAbilities()->RestoreResource();
    ClientWorldEditResult(TEXT("Health, mana and class resource restored."));
}
void AWarPlayerController::ServerGmResetCooldowns_Implementation()
{
    FString Error;
    if (!Authorized(this,Error)) { ClientWorldEditResult(Error); return; }
    auto* State = GetPlayerState<AWarPlayerState>();
    auto* ASC = State ? State->GetAbilitySystemComponent() : nullptr;
    if (!ASC) { ClientWorldEditResult(TEXT("Ability state unavailable.")); return; }
    FGameplayTagContainer CooldownTags;
    CooldownTags.AddTag(FGameplayTag::RequestGameplayTag(TEXT("War.Cooldown.DevelopmentStrike")));
    const int32 Removed=ASC->RemoveActiveEffectsWithGrantedTags(CooldownTags);
    State->GetClassAbilities()->ResetCooldowns();
    ClientWorldEditResult(FString::Printf(TEXT("Cleared class cooldowns and %d basic-strike cooldown effect(s)."),Removed));
}
void AWarPlayerController::ServerGmGoToCharacter_Implementation(const FString& Name)
{
    FString Error;
    if (!Authorized(this,Error)) { ClientWorldEditResult(Error); return; }
    if (!WarGmRules::ValidCharacterQuery(Name)) { ClientWorldEditResult(TEXT("Enter an exact character name, up to 32 characters.")); return; }
    AWarCharacter* Target=nullptr;
    int32 Matches = 0;
    for (TActorIterator<AWarPlayerState> It(GetWorld()); It; ++It)
        if (It->GetPlayerName().Equals(Name.TrimStartAndEnd(),ESearchCase::IgnoreCase))
        {
            if (++Matches > 1) { ClientWorldEditResult(TEXT("Multiple characters match. Use a unique character name.")); return; }
            Target=Cast<AWarCharacter>(It->GetPawn());
        }
    if (!Target || Target->IsDead() || !Target->IsVisualReady())
    { ClientWorldEditResult(TEXT("No available character with that exact name is in this world. Saved/offline lookup is not connected.")); return; }
    const FVector Position=Target->GetActorLocation()+Target->GetActorRightVector()*250;
    const bool Success=Land(this,Position,Error);
    ClientWorldEditResult(Success ? TEXT("Teleported beside ")+Name.TrimStartAndEnd() : Error);
}
void AWarPlayerController::ServerGmTeleportZone_Implementation(FName Zone)
{
    FString Error;
    if (!Authorized(this,Error)) { ClientWorldEditResult(Error); return; }
    if (auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
        Streaming && AWarZoneAnchor::FindById(GetWorld(), Zone) && !Streaming->IsZoneReady(Zone, this))
    {
        Streaming->QueueGmZone(this, Zone, Error);
        ClientWorldEditResult(Error); return;
    }
    // Only trusted, reciprocal, loaded portal arrivals can supply a destination.
    const FString Prefix=Zone.ToString()+TEXT("_to_");
    for (TActorIterator<AWarZonePortal> It(GetWorld()); It; ++It)
    {
        if (!It->bDestinationBuilt || !It->DestinationRouteId.ToString().StartsWith(Prefix)) continue;
        AWarZonePortal* Destination=nullptr;
        for (TActorIterator<AWarZonePortal> Other(GetWorld()); Other; ++Other)
            if (Other->bDestinationBuilt && Other->RouteId == It->DestinationRouteId && Other->DestinationRouteId == It->RouteId)
            { Destination=*Other; break; }
        if (!Destination) continue;
        ClientWorldEditResult(Land(this,It->ArrivalLocation,Error) ? TEXT("Teleported to ")+Zone.ToString() : Error); return;
    }
    if (Zone==TEXT("aegis_capital"))
    {
        if (auto* GmPawn=Cast<AWarCharacter>(GetPawn()))
        { ClientWorldEditResult(GmPawn->ReturnToDevelopmentSpawn(Error) ? TEXT("Returned to Bastion of Aegis arrival.") : Error); return; }
    }
    ClientWorldEditResult(TEXT("This zone has no validated, loaded native arrival. Build and load its destination before teleporting."));
}
void AWarPlayerController::ServerResetWorldDraft_Implementation(int32 Revision)
{
    auto* Editor=GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); FString Error;
    const bool Success=Editor && Editor->ResetDraft(this,Revision,Error);
    ClientWorldEditResult(Success ? TEXT("Draft reset to the authored world. Undo restores the previous draft; Save writes the reset.") : Error);
}
void AWarPlayerController::ServerDuplicateWorldObject_Implementation(FName Id,int32 Revision)
{
    auto* Editor=GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); FString Error; FName Created;
    const bool Success=Editor && Editor->Duplicate(this,Id,Revision,Created,Error);
    if (Success) ClientWorldObjectCreated(Created);
    ClientWorldEditResult(Success ? TEXT("Duplicated the selected model. Move or snap the copy before saving.") : Error);
}
void AWarPlayerController::MeasureWorldObject(FName Id)
{
    auto* Editor=GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    auto* Actor=Editor && Editor->CanUse(this) ? Editor->GetObjectActor(Id) : nullptr;
    if (!Actor || !GetPawn()) return;
    const FBox Bounds=Actor->GetComponentsBoundingBox(true);
    const FVector Size=Bounds.GetSize()/100;
    WorldEditMessage=FString::Printf(TEXT("Bounds: %.2f x %.2f x %.2f m | Distance from you: %.2f m"),
        Size.X,Size.Y,Size.Z,FVector::Dist(GetPawn()->GetActorLocation(),Bounds.GetCenter())/100);
}
