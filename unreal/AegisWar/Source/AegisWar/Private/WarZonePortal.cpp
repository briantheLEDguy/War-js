#include "WarZonePortal.h"
#include "WarCharacter.h"
#include "WarGameMode.h"
#include "WarSiegeEncounter.h"
#include "WarCampaignSiegeSubsystem.h"
#include "WarZoneAnchor.h"
#include "WarZoneStreamingSubsystem.h"
#include "WarPortalLanding.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "Components/SphereComponent.h"
#include "Components/TextRenderComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"

AWarZonePortal::AWarZonePortal()
{
    bReplicates = true;
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = 0.1f;
    Trigger = CreateDefaultSubobject<USphereComponent>(TEXT("PortalTrigger"));
    SetRootComponent(Trigger);
    Trigger->SetCollisionProfileName(TEXT("Trigger"));
    Trigger->SetSphereRadius(Radius);
    Trigger->OnComponentBeginOverlap.AddDynamic(this, &AWarZonePortal::Enter);
    Label = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Destination"));
    Label->SetupAttachment(Trigger);
    Label->SetRelativeLocation(FVector(0, 0, 350));
    Label->SetHorizontalAlignment(EHTA_Center);
    Label->SetWorldSize(60);
}

void AWarZonePortal::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    Trigger->SetSphereRadius(FMath::Clamp(Radius, 100.f, 2000.f));
    // Text render components are stripped when this authored level loads on a dedicated server.
    if (!Label) return;
    Label->SetText(FText::FromString(DestinationLabel.ToString() + (bDestinationBuilt ? TEXT("\nZone portal") : TEXT("\nDestination under construction"))));
    Label->SetTextRenderColor(bDestinationBuilt ? FColor(100, 220, 255) : FColor(230, 180, 90));
}

bool AWarZonePortal::CanEnter(bool bAuthority, bool bDevelopment, bool bAlive, bool bVisualReady,
    bool bDestinationReady, double Distance, double EntryRadius, double Now, double AllowedAt)
{
    return bAuthority && bDevelopment && bAlive && bVisualReady && bDestinationReady
        && FMath::IsFinite(Distance) && Distance >= 0 && FMath::IsFinite(EntryRadius) && EntryRadius > 0
        && Distance <= EntryRadius && FMath::IsFinite(Now) && FMath::IsFinite(AllowedAt) && Now >= AllowedAt;
}

double AWarZonePortal::CapsuleGroundOffset(double HalfHeight, double CapsuleRadius, double NormalZ)
{
    // A vertical capsule's lower hemisphere needs additional height on a walkable slope.
    return HalfHeight + CapsuleRadius * (1.0 / FMath::Clamp(NormalZ, 0.7, 1.0) - 1.0) + 5.0;
}

bool AWarZonePortal::IsWithinEntryRange(const AActor* Actor) const
{
    return IsValid(Actor) && FVector::DistSquared(Actor->GetActorLocation(), GetActorLocation())
        <= FMath::Square(Trigger->GetScaledSphereRadius());
}

void AWarZonePortal::AttemptEntry(AWarCharacter* Character)
{
    if (!HasAuthority() || !IsWithinEntryRange(Character) || AttemptedInside.Contains(Character)) return;
    if (!Character->GetController() || !Character->IsVisualReady() || Character->IsDead()) return;
    AttemptedInside.Add(Character);
    FString Error;
    if (!TryTraverse(Character, Error))
        if (auto* Player = Cast<AWarPlayerController>(Character->GetController())) Player->ClientZoneTravelStatus(Error);
}

void AWarZonePortal::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!HasAuthority() || !GetActorEnableCollision()) return;
    for (auto It = AttemptedInside.CreateIterator(); It; ++It)
        if (!IsWithinEntryRange(It->Get())) It.RemoveCurrent();
    for (auto It = AllowedAfter.CreateIterator(); It; ++It)
        if (!It.Key().IsValid() || It.Value() < GetWorld()->GetTimeSeconds()) It.RemoveCurrent();
    // Capsule contact precedes center entry. BeginOverlap alone misses walking farther
    // into the sphere; player polling also covers levels loaded around an existing pawn.
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (auto* Player = It->Get()) AttemptEntry(Cast<AWarCharacter>(Player->GetPawn()));
}

bool AWarZonePortal::BlocksSiegeDeparture(const AWarCharacter* Character, FName Destination)
{
    const auto* State = Character ? Character->GetPlayerState<AWarPlayerState>() : nullptr;
    const auto* Encounter = State ? State->GetSiegeEncounter() : nullptr;
    if (!Encounter || Destination == TEXT("aegis_capital")) return false;
    // A remote reserved seat must retain its normal approach routes until physical admission.
    return !Encounter->bCampaign || Encounter->IsCapitalOccupant(Character);
}

bool AWarZonePortal::TryTraverse(AWarCharacter* Character, FString& Error, bool bEvacuating)
{
    const auto* EvacuationBridge = GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>();
    const bool HeldEvacuation = bEvacuating && EvacuationBridge && EvacuationBridge->HasEvacuationCheckpoint(Cast<AWarPlayerController>(Character ? Character->GetController() : nullptr));
    if (const auto* State = Character ? Character->GetPlayerState<AWarPlayerState>() : nullptr;
        State && State->IsScenarioTransferPending() && !HeldEvacuation)
    { Error = TEXT("Scenario departure is in progress."); return false; }
    const auto* Mode = GetWorld()->GetAuthGameMode<AWarGameMode>();
    const auto* Siege = AWarSiegeEncounter::For(Character);
    const auto* PS = Character ? Character->GetPlayerState<AWarPlayerState>() : nullptr;
    const bool Evacuation = bEvacuating && HasAuthority() && Siege && PS && PS->GetCurrentZone() == TEXT("aegis_capital") && Siege->BlocksCapitalEntry(PS);
    const double Now = GetWorld()->GetTimeSeconds();
    if (!Character || !Character->GetController() || !CanEnter(HasAuthority(), Mode && Mode->IsDevelopmentSession(),
        !Character->IsDead(), Character->IsVisualReady(), bDestinationBuilt,
        Evacuation ? 0. : FVector::Dist(Character->GetActorLocation(), GetActorLocation()), Trigger->GetScaledSphereRadius(), Now,
        Evacuation ? 0. : AllowedAfter.FindRef(Character)))
    {
        Error = TEXT("Portal unavailable, out of range, or still cooling down.");
        return false;
    }
    AWarZonePortal* Destination = nullptr;
    for (TActorIterator<AWarZonePortal> It(GetWorld()); It; ++It)
        if (It->RouteId == DestinationRouteId && It->DestinationRouteId == RouteId && It->bDestinationBuilt)
        {
            if (Destination) { Error = TEXT("Ambiguous destination portal."); return false; }
            Destination = *It;
        }
    if (!Destination || Destination == this || RouteId.IsNone() || ArrivalLocation.ContainsNaN())
    { Error = TEXT("Destination is not loaded. Stay here and retry after the zone is built."); return false; }

    const auto* DestinationZone = AWarZoneAnchor::FindAt(GetWorld(), ArrivalLocation);
    auto* Streaming = GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
    if (!DestinationZone) { Error = TEXT("Destination has no unambiguous zone anchor."); return false; }
    if (!Siege && DestinationZone->ZoneId == TEXT("aegis_capital"))
        for (TActorIterator<AWarSiegeEncounter> It(GetWorld()); It; ++It) if (It->bCampaign) { Siege = *It; break; }
    if (Evacuation && (!Siege->CanEvacuate(PS->GetRealm(), DestinationZone->ZoneId)))
    { Error = TEXT("Evacuation destination is no longer owned and secured by your realm."); return false; }
    if (Siege && DestinationZone->ZoneId == TEXT("aegis_capital") && Siege->BlocksCapitalEntry(PS))
    { Error = TEXT("Enroll in the active siege before entering the capital."); return false; }
    if (!Evacuation && BlocksSiegeDeparture(Character, DestinationZone->ZoneId))
    { Error = TEXT("Leave the siege before traveling to another zone."); return false; }
    if (Streaming && !Streaming->IsZoneReady(DestinationZone->ZoneId, Cast<APlayerController>(Character->GetController())))
        return Streaming->QueuePortal(this, Character, DestinationZone->ZoneId, Error, Evacuation);

    FVector Landing;
    const float SearchRadius=Evacuation ? FMath::Clamp(Destination->Trigger->GetScaledSphereRadius()
        -Character->GetCapsuleComponent()->GetScaledCapsuleRadius()-5,0.f,600.f) : 0.f;
    if (!WarPortalLanding::Find(Character,ArrivalLocation,DestinationZone,SearchRadius,this,Destination,Landing,Error)) return false;
    const double Previous = Destination->AllowedAfter.FindRef(Character);
    Destination->AllowedAfter.Add(Character, Now + 3.0);
    if (!Character->TeleportTo(Landing, Character->GetActorRotation()))
    {
        Destination->AllowedAfter.Add(Character, Previous);
        Error = TEXT("Destination landing is obstructed."); return false;
    }
    Error = Evacuation ? TEXT("Evacuated to a safe neighboring zone.") : FString();
    AllowedAfter.Add(Character, Now + 3.0);
    if (Streaming) Streaming->Cancel(Character);
    if (const auto* Anchor = AWarZoneAnchor::FindAt(GetWorld(), Character->GetActorLocation()))
        if (auto* State = Character->GetPlayerState<AWarPlayerState>()) State->SetCurrentZoneTrusted(Anchor->ZoneId);
    Character->GetCharacterMovement()->StopMovementImmediately();
    if (Character->IsAutoRunning()) Character->ToggleAutoRun();
    Character->ForceNetUpdate();
    if (auto* Player = Cast<AWarPlayerController>(Character->GetController()))
    { Player->ClientZoneTravelStatus(FString()); if (Evacuation) if (auto* Bridge = GetWorld()->GetSubsystem<UWarCampaignSiegeSubsystem>()) Bridge->Evacuated(Player); }
    return true;
}

void AWarZonePortal::Enter(UPrimitiveComponent* Component, AActor* Other, UPrimitiveComponent* OtherComponent,
    int32 BodyIndex, bool bSweep, const FHitResult& Hit)
{
    AttemptEntry(Cast<AWarCharacter>(Other));
}
