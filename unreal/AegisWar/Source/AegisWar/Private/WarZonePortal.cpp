#include "WarZonePortal.h"
#include "WarCharacter.h"
#include "WarGameMode.h"
#include "WarZoneAnchor.h"
#include "WarZoneStreamingSubsystem.h"
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

bool AWarZonePortal::TryTraverse(AWarCharacter* Character, FString& Error)
{
    const auto* Mode = GetWorld()->GetAuthGameMode<AWarGameMode>();
    const double Now = GetWorld()->GetTimeSeconds();
    if (!Character || !Character->GetController() || !CanEnter(HasAuthority(), Mode && Mode->IsDevelopmentSession(),
        !Character->IsDead(), Character->IsVisualReady(), bDestinationBuilt,
        FVector::Dist(Character->GetActorLocation(), GetActorLocation()), Trigger->GetScaledSphereRadius(), Now,
        AllowedAfter.FindRef(Character)))
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
    if (Streaming && !Streaming->IsZoneReady(DestinationZone->ZoneId, Cast<APlayerController>(Character->GetController())))
        return Streaming->QueuePortal(this, Character, DestinationZone->ZoneId, Error);

    // Only land on real blocking ground; missing terrain must never strand a player in the void.
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PortalLanding), false, Character);
    Query.AddIgnoredActor(this); Query.AddIgnoredActor(Destination);
    FHitResult Ground;
    if (!GetWorld()->LineTraceSingleByChannel(Ground, ArrivalLocation + FVector(0, 0, 5000),
        ArrivalLocation - FVector(0, 0, 5000), ECC_WorldStatic, Query) || Ground.ImpactNormal.Z < 0.7)
    { Error = TEXT("Destination has no safe landing surface."); return false; }
    const FVector Landing = Ground.ImpactPoint + FVector(0, 0, CapsuleGroundOffset(
        Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),
        Character->GetCapsuleComponent()->GetScaledCapsuleRadius(), Ground.ImpactNormal.Z));
    if (GetWorld()->OverlapBlockingTestByProfile(Landing, FQuat::Identity, TEXT("Pawn"),
        FCollisionShape::MakeCapsule(Character->GetCapsuleComponent()->GetScaledCapsuleRadius(),
            Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), Query))
    { Error = TEXT("Destination landing is obstructed."); return false; }
    const double Previous = Destination->AllowedAfter.FindRef(Character);
    Destination->AllowedAfter.Add(Character, Now + 3.0);
    if (!Character->TeleportTo(Landing, Character->GetActorRotation()))
    {
        Destination->AllowedAfter.Add(Character, Previous);
        Error = TEXT("Destination landing is obstructed."); return false;
    }
    AllowedAfter.Add(Character, Now + 3.0);
    if (Streaming) Streaming->Cancel(Character);
    if (const auto* Anchor = AWarZoneAnchor::FindAt(GetWorld(), Character->GetActorLocation()))
        if (auto* State = Character->GetPlayerState<AWarPlayerState>()) State->SetCurrentZoneTrusted(Anchor->ZoneId);
    Character->GetCharacterMovement()->StopMovementImmediately();
    if (Character->IsAutoRunning()) Character->ToggleAutoRun();
    Character->ForceNetUpdate();
    if (auto* Player = Cast<AWarPlayerController>(Character->GetController())) Player->ClientZoneTravelStatus(FString());
    return true;
}

void AWarZonePortal::Enter(UPrimitiveComponent* Component, AActor* Other, UPrimitiveComponent* OtherComponent,
    int32 BodyIndex, bool bSweep, const FHitResult& Hit)
{
    if (!HasAuthority()) return;
    for (auto It = AllowedAfter.CreateIterator(); It; ++It)
        if (!It.Key().IsValid() || It.Value() < GetWorld()->GetTimeSeconds()) It.RemoveCurrent();
    FString Error;
    if (auto* Character = Cast<AWarCharacter>(Other))
        if (!TryTraverse(Character, Error))
        {
            if (auto* Player = Cast<AWarPlayerController>(Character->GetController())) Player->ClientZoneTravelStatus(Error);
            UE_LOG(LogTemp, Verbose, TEXT("Portal %s: %s"), *RouteId.ToString(), *Error);
        }
}
