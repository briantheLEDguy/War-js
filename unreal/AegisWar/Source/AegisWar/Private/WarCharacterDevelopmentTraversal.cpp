#include "WarCharacter.h"
#include "WarPlayerController.h"
#include "WarWorldEditSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameModeBase.h"
#include "Engine/World.h"

namespace
{
    bool ClearCharacterSpace(const AWarCharacter* Character, const FVector Position)
    {
        const auto* Capsule = Character->GetCapsuleComponent();
        FCollisionQueryParams Query; Query.AddIgnoredActor(Character);
        return !Character->GetWorld()->OverlapBlockingTestByProfile(Position, FQuat::Identity,
            Capsule->GetCollisionProfileName(), FCollisionShape::MakeCapsule(
                Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight()), Query);
    }
}

bool AWarCharacter::SetDevelopmentTraversal(const bool bFlying, const float SpeedMultiplier, FString& Error)
{
    const auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    if (!HasAuthority() || !Editor || !Editor->CanUse(Cast<AWarPlayerController>(Controller)) || bDead || !bVisualReady)
    { Error = TEXT("Development GM traversal is unavailable for this session."); return false; }
    if (!FMath::IsFinite(SpeedMultiplier) || SpeedMultiplier < 0.25f || SpeedMultiplier > 6.f)
    { Error = TEXT("GM speed must be between 0.25x and 6x."); return false; }
    if (bDevelopmentFlying && !bFlying && !ClearCharacterSpace(this, GetActorLocation()))
    { Error = TEXT("Move into clear space before leaving flight."); return false; }
    auto* Movement = GetCharacterMovement();
    if (!bDevelopmentSpeedsCaptured)
    {
        DevelopmentBaseWalkSpeed = Movement->MaxWalkSpeed;
        DevelopmentBaseFlySpeed = Movement->MaxFlySpeed;
        DevelopmentBaseBraking = Movement->BrakingDecelerationFlying;
        DevelopmentCollision = GetCapsuleComponent()->GetCollisionEnabled();
        bDevelopmentSpeedsCaptured = true;
    }
    DevelopmentSpeed = SpeedMultiplier;
    Movement->MaxWalkSpeed = DevelopmentBaseWalkSpeed * SpeedMultiplier;
    Movement->MaxFlySpeed = bFlying ? DevelopmentBaseWalkSpeed * SpeedMultiplier : DevelopmentBaseFlySpeed;
    Movement->BrakingDecelerationFlying = bFlying ? 4096.f * SpeedMultiplier : DevelopmentBaseBraking;
    if (bDevelopmentFlying != bFlying)
    {
        // Browser GM flight bypasses world collision. Only the explicitly
        // authorized local development capital may enable this native path.
        bDevelopmentFlying = bFlying;
        MovementInput.bAutoRun = false;
        Movement->StopMovementImmediately();
        GetCapsuleComponent()->SetCollisionEnabled(bFlying ? ECollisionEnabled::NoCollision : DevelopmentCollision);
        Movement->SetMovementMode(bFlying ? MOVE_Flying : MOVE_Falling);
    }
    return true;
}

bool AWarCharacter::ReturnToDevelopmentSpawn(FString& Error)
{
    const auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    if (!HasAuthority() || !Editor || !Editor->CanUse(Cast<AWarPlayerController>(Controller)) || bDead || !bVisualReady)
    { Error = TEXT("Development GM traversal is unavailable for this session."); return false; }
    auto* Mode = GetWorld()->GetAuthGameMode();
    AActor* Start = Mode ? Mode->FindPlayerStart(Controller) : nullptr;
    if (!Start || !ClearCharacterSpace(this, Start->GetActorLocation())
        || !TeleportTo(Start->GetActorLocation(), GetActorRotation(), false, false))
    { Error = TEXT("The capital arrival is blocked or unavailable."); return false; }
    MovementInput.bAutoRun = false;
    GetCharacterMovement()->StopMovementImmediately();
    return true;
}
