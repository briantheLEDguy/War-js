#include "WarOverheadHealth.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarAttributeSet.h"

bool WarOverheadHealth::Read(const AWarPlayerController* Viewer, const AActor* Recipient, FWarOverheadHealth& Out)
{
    Out = {};
    // Reuse combat visibility, zone, model readiness and 50-metre range policy.
    if (!IsValid(Viewer) || !Viewer->IsCombatTarget(Recipient)) return false;
    float Health = 0, Maximum = 0;
    if (const auto* Enemy = Cast<AWarEnemy>(Recipient))
    {
        Health = Enemy->GetHealth(); Maximum = Enemy->GetDefinition().MaxHealth;
    }
    else if (const auto* Character = Cast<AWarCharacter>(Recipient))
    {
        const auto* State = Character->GetPlayerState<AWarPlayerState>();
        const auto* Attributes = State ? State->GetAttributes() : nullptr;
        if (!Attributes) return false;
        Health = Attributes->GetHealth(); Maximum = Attributes->GetMaxHealth();
    }
    if (!FMath::IsFinite(Health) || !FMath::IsFinite(Maximum) || Health <= 0 || Maximum <= 0) return false;
    Out.Fraction = FMath::Clamp(Health / Maximum, 0.f, 1.f);
    Out.bEnemy = Viewer->IsEnemyCombatTarget(Recipient);
    return true;
}

FBox2D WarOverheadHealth::Bounds(FVector2D Head, FVector2D Viewport, float Scale)
{
    if (Head.ContainsNaN() || Viewport.ContainsNaN() || !FMath::IsFinite(Scale) || Scale <= 0
        || Viewport.X <= 0 || Viewport.Y <= 0) return FBox2D(ForceInit);
    const FBox2D Rect(Head - FVector2D(Width * .5f, Height) * Scale,
        Head + FVector2D(Width * .5f * Scale, 0));
    return Rect.Min.X >= 0 && Rect.Min.Y >= 0 && Rect.Max.X <= Viewport.X && Rect.Max.Y <= Viewport.Y
        ? Rect : FBox2D(ForceInit);
}
